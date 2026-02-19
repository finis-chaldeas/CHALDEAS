"""
LLM Event Validator - 이벤트가 진짜인지 쓰레기인지 판단

로컬 Ollama 사용 (llama3.1:8b)
"""
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import httpx

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_PATH = SCRIPT_DIR.parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH))
os.chdir(BACKEND_PATH.parent)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.db.session import SessionLocal

# Ollama settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_0")


VALIDATION_PROMPT = """You are a historian. Analyze if this is a real historical event or garbage data.

Event: {title}
Year: {year}
Connected persons: {person_count}
Connected locations: {location_count}

Answer in JSON format:
{{
    "is_real": true/false,
    "confidence": "high"/"medium"/"low",
    "reason": "brief explanation",
    "suggested_name": "corrected name if applicable, null otherwise"
}}

Rules:
- Generic words like "Battle", "Treaty", "Death", "Publication" alone are GARBAGE
- "Battle of [Place]" or "[Name] War" are likely REAL
- If unsure, say confidence "low"

Respond ONLY with JSON, no other text."""


@dataclass
class ValidationResult:
    event_id: int
    event_title: str
    is_real: bool
    confidence: str
    reason: str
    suggested_name: Optional[str] = None
    error: Optional[str] = None


def validate_with_ollama(title: str, year: int, person_count: int, location_count: int) -> dict:
    """Ollama로 이벤트 검증"""
    prompt = VALIDATION_PROMPT.format(
        title=title,
        year=year or "unknown",
        person_count=person_count,
        location_count=location_count
    )

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()

        # Parse JSON from response
        text = result.get("response", "")
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": f"JSON parse error: {text[:100]}"}
    except Exception as e:
        return {"error": str(e)[:100]}


def validate_events(limit: int = 50, dry_run: bool = True, quarantine: bool = False, output_file: str = None):
    """이벤트 검증 실행"""
    db = SessionLocal()

    try:
        print("=== LLM Event Validator ===")
        print(f"Model: {OLLAMA_MODEL}")
        print(f"URL: {OLLAMA_URL}")
        print()

        # 의심스러운 이벤트 추출 (WD 없고, 소스 없고)
        events = db.execute(text('''
            SELECT e.id, e.title, e.date_start,
                   (SELECT COUNT(*) FROM event_persons ep WHERE ep.event_id = e.id) as person_count,
                   (SELECT COUNT(*) FROM event_locations el WHERE el.event_id = e.id) as location_count
            FROM events e
            WHERE e.wikidata_id IS NULL
              AND e.wikipedia_url IS NULL
              AND NOT EXISTS (SELECT 1 FROM event_sources es WHERE es.event_id = e.id)
              AND e.parent_status NOT IN ('garbage', 'pending')  -- 이미 처리된 건 제외
            ORDER BY person_count DESC
            LIMIT :limit
        '''), {'limit': limit}).fetchall()

        print(f"Validating {len(events)} suspicious events...\n")

        results = []
        garbage_ids = []
        real_ids = []

        for i, (eid, title, year, p_cnt, l_cnt) in enumerate(events):
            print(f"[{i+1}/{len(events)}] {title} (p={p_cnt}, l={l_cnt})...", end=" ", flush=True)

            result = validate_with_ollama(title, year, p_cnt, l_cnt)

            if "error" in result:
                print(f"ERROR: {result['error']}")
                results.append(ValidationResult(
                    event_id=eid, event_title=title,
                    is_real=True, confidence="low", reason="",
                    error=result["error"]
                ))
            else:
                is_real = result.get("is_real", True)
                conf = result.get("confidence", "low")
                reason = result.get("reason", "")[:100]

                if is_real:
                    print(f"REAL ({conf})")
                    real_ids.append(eid)
                else:
                    print(f"GARBAGE ({conf}) - {reason}")
                    garbage_ids.append(eid)

                results.append(ValidationResult(
                    event_id=eid, event_title=title,
                    is_real=is_real, confidence=conf, reason=reason,
                    suggested_name=result.get("suggested_name")
                ))

        # Categorize by confidence
        high_conf_garbage = [r for r in results if not r.is_real and r.confidence == "high" and not r.error]
        low_conf = [r for r in results if r.confidence in ("low", "medium") and not r.error]
        high_conf_real = [r for r in results if r.is_real and r.confidence == "high" and not r.error]
        errors = [r for r in results if r.error]

        # Summary
        print(f"\n=== Summary ===")
        print(f"확실한 REAL: {len(high_conf_real)}")
        print(f"확실한 GARBAGE: {len(high_conf_garbage)}")
        print(f"애매함 (GPT-5.1 필요): {len(low_conf)}")
        print(f"에러: {len(errors)}")

        # Save uncertain ones for GPT-5.1 review
        if output_file and low_conf:
            uncertain_data = [
                {
                    "event_id": r.event_id,
                    "event_title": r.event_title,
                    "is_real": r.is_real,
                    "confidence": r.confidence,
                    "reason": r.reason
                }
                for r in low_conf
            ]
            Path(output_file).write_text(json.dumps(uncertain_data, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"\n애매한 것 저장: {output_file}")

        if high_conf_garbage and quarantine and not dry_run:
            print(f"\n=== Quarantining {len(high_conf_garbage)} garbage events ===")
            for r in high_conf_garbage:
                db.execute(text('''
                    UPDATE events SET parent_status = 'garbage'
                    WHERE id = :id
                '''), {'id': r.event_id})
            db.commit()
            print(f"Marked {len(high_conf_garbage)} events as garbage")

        # Mark validated REAL events as pending (so they're not re-processed)
        high_conf_real = [r for r in results if r.is_real and r.confidence == "high"]
        if high_conf_real and not dry_run:
            print(f"\n=== Marking {len(high_conf_real)} real events as pending ===")
            for r in high_conf_real:
                db.execute(text('''
                    UPDATE events SET parent_status = 'pending'
                    WHERE id = :id AND parent_status = 'unknown'
                '''), {'id': r.event_id})
            db.commit()
            print(f"Marked {len(high_conf_real)} events as pending")

        if dry_run:
            print(f"\n[DRY RUN] No changes made.")
            if high_conf_garbage:
                print(f"Would quarantine: {[r.event_id for r in high_conf_garbage[:20]]}...")

        return results

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate events with LLM")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    parser.add_argument("--quarantine", action="store_true", help="Quarantine garbage events")
    parser.add_argument("--output", "-o", type=str, help="Save uncertain events for GPT-5.1 review")

    args = parser.parse_args()
    validate_events(
        limit=args.limit,
        dry_run=not args.apply,
        quarantine=args.quarantine,
        output_file=args.output
    )
