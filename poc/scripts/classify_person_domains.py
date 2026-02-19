"""
Classify persons into historical domains using LLM.

Each person is assigned a primary domain (e.g., science, military, literature)
based on their name, role, and description. This enables domain-specific
importance scoring and filtered timelines.

Uses gpt-5-mini with batches of 50 persons.
~190K persons → ~3,800 API calls → ~$2-3

Usage:
    python classify_person_domains.py              # Classify all
    python classify_person_domains.py --limit 100  # Test with 100
    python classify_person_domains.py --stats       # Show domain stats from checkpoint
"""
import sys
import os
import json
import time
import asyncio
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

from openai import AsyncOpenAI
from sqlalchemy import create_engine, text

# ── Config ──
MODEL = "gpt-5-mini"
MAX_CONCURRENT = 500
BATCH_SIZE = 50              # Persons per API call
CHECKPOINT_DIR = Path(__file__).parent.parent / "data" / "importance_scores"

engine = create_engine('postgresql://chaldeas:chaldeas_dev@localhost:5432/chaldeas')
aclient = AsyncOpenAI()


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN TAXONOMY — 역사학 분과 기반 16개 도메인
# ═══════════════════════════════════════════════════════════════════════════════
#
# 각 도메인은 역사학의 확립된 하위분야에 대응하며,
# 해당 분야 내에서의 상대적 중요도 평가를 가능하게 함.
#
# global_weight: 세계사 타임라인에서의 가중치 (도메인 점수 × 가중치 = 글로벌 점수)
# 예: science 95점 × 0.90 = 85.5 글로벌  vs  entertainment 95점 × 0.35 = 33.3 글로벌
# ═══════════════════════════════════════════════════════════════════════════════

DOMAINS = {
    # ── 권력/정치사 ──
    "statecraft": {
        "name_en": "Statecraft & Governance",
        "name_ko": "정치/통치",
        "field": "Political History",
        "desc": "Rulers, heads of state, monarchs, emperors, presidents, prime ministers, "
                "politicians, diplomats, lawmakers, ministers, governors",
        "global_weight": 1.0,
    },
    "military": {
        "name_en": "Military & Warfare",
        "name_ko": "군사/전쟁",
        "field": "Military History",
        "desc": "Generals, admirals, warriors, conquerors, military strategists, "
                "soldiers, commanders, resistance fighters, pirates",
        "global_weight": 0.95,
    },

    # ── 사상/정신사 ──
    "religion": {
        "name_en": "Religion & Theology",
        "name_ko": "종교/신학",
        "field": "Religious History",
        "desc": "Prophets, saints, religious founders, popes, patriarchs, imams, "
                "monks, missionaries, theologians, mystics, clergy",
        "global_weight": 1.0,
    },
    "philosophy": {
        "name_en": "Philosophy & Ideas",
        "name_ko": "사상/철학",
        "field": "History of Ideas (Intellectual History)",
        "desc": "Philosophers, political theorists, ethicists, logicians, "
                "ideologists, social thinkers, metaphysicians",
        "global_weight": 0.90,
    },

    # ── 과학/기술사 ──
    "science": {
        "name_en": "Science & Mathematics",
        "name_ko": "과학/수학",
        "field": "History of Science",
        "desc": "Scientists, mathematicians, physicists, chemists, biologists, "
                "astronomers, geologists, naturalists, zoologists, botanists",
        "global_weight": 0.90,
    },
    "medicine": {
        "name_en": "Medicine & Health",
        "name_ko": "의학/보건",
        "field": "History of Medicine",
        "desc": "Physicians, surgeons, medical researchers, pharmacologists, "
                "epidemiologists, psychiatrists, nurses, public health pioneers",
        "global_weight": 0.80,
    },
    "technology": {
        "name_en": "Technology & Invention",
        "name_ko": "기술/발명",
        "field": "History of Technology",
        "desc": "Inventors, engineers, architects, industrialists who built things, "
                "computing pioneers, aviation pioneers",
        "global_weight": 0.85,
    },

    # ── 문화/예술사 ──
    "literature": {
        "name_en": "Literature & Letters",
        "name_ko": "문학",
        "field": "Literary History",
        "desc": "Writers, novelists, poets, playwrights, essayists, "
                "literary critics, screenwriters",
        "global_weight": 0.80,
    },
    "visual_arts": {
        "name_en": "Visual Arts",
        "name_ko": "미술/시각예술",
        "field": "Art History",
        "desc": "Painters, sculptors, photographers, printmakers, "
                "calligraphers, illustrators, graphic designers",
        "global_weight": 0.75,
    },
    "music": {
        "name_en": "Music & Performing Arts",
        "name_ko": "음악/공연예술",
        "field": "History of Music",
        "desc": "Composers, musicians, singers, conductors, opera performers, "
                "dancers, choreographers, theater directors",
        "global_weight": 0.70,
    },

    # ── 사회/경제사 ──
    "exploration": {
        "name_en": "Exploration & Geography",
        "name_ko": "탐험/지리",
        "field": "History of Exploration",
        "desc": "Explorers, navigators, cartographers, geographers, "
                "mountaineers, astronauts, colonial pioneers",
        "global_weight": 0.85,
    },
    "economy": {
        "name_en": "Economy & Commerce",
        "name_ko": "경제/상업",
        "field": "Economic History",
        "desc": "Merchants, economists, bankers, traders, industrialists (as businessmen), "
                "financiers, entrepreneurs",
        "global_weight": 0.65,
    },
    "law": {
        "name_en": "Law & Jurisprudence",
        "name_ko": "법학/제도",
        "field": "Legal History",
        "desc": "Jurists, judges, legal scholars, constitutional framers, "
                "prosecutors, legal reformers",
        "global_weight": 0.70,
    },
    "reform": {
        "name_en": "Social Reform & Activism",
        "name_ko": "사회개혁/운동",
        "field": "Social History",
        "desc": "Activists, social reformers, abolitionists, revolutionaries, "
                "civil rights leaders, labor organizers, feminists, dissidents",
        "global_weight": 0.80,
    },

    # ── 학술/교육 ──
    "scholarship": {
        "name_en": "Scholarship & Historiography",
        "name_ko": "학문/역사서술",
        "field": "Historiography / History of Education",
        "desc": "Historians, chroniclers, educators, encyclopedists, "
                "librarians, linguists, translators, archivists, polymaths",
        "global_weight": 0.60,
    },

    # ── 현대 문화 ──
    "entertainment": {
        "name_en": "Entertainment & Sports",
        "name_ko": "엔터테인먼트/스포츠",
        "field": "Cultural History / Popular Culture",
        "desc": "Athletes, actors, filmmakers, game designers, "
                "media figures, comedians, modern entertainers, sports figures",
        "global_weight": 0.35,
    },
}

DOMAIN_IDS = sorted(DOMAINS.keys())

# Build the classification prompt once
def _build_domain_list():
    lines = []
    for i, (did, d) in enumerate(sorted(DOMAINS.items()), 1):
        lines.append(f"  {did}: {d['desc']}")
    return "\n".join(lines)

DOMAIN_LIST_STR = _build_domain_list()

CLASSIFY_PROMPT = """Classify each person into ONE primary historical domain.
Choose the domain for which the person is MOST historically remembered.

Domains:
{domain_list}

Persons to classify:
{persons_block}

Respond with ONLY a JSON array in the same order:
[{{"id": <id>, "domain": "<domain_id>"}}, ...]"""


# ── Data loading ──

def load_persons(limit: int = 0) -> list[dict]:
    """Load persons from DB."""
    q = """
        SELECT p.id, p.name, p.birth_year, p.death_year,
               p.role, LEFT(p.description, 120) as description
        FROM persons p
        WHERE p.wikidata_id IS NOT NULL
        ORDER BY p.id
    """
    if limit > 0:
        q += f" LIMIT {limit}"

    with engine.connect() as conn:
        rows = conn.execute(text(q)).fetchall()

    persons = []
    for r in rows:
        dates = ""
        if r[2]:
            dates = f"{abs(r[2])} {'BCE' if r[2] < 0 else 'CE'}"
        if r[3]:
            dates += f" - {abs(r[3])} {'BCE' if r[3] < 0 else 'CE'}"

        persons.append({
            "id": r[0],
            "name": r[1],
            "dates": dates,
            "role": r[4] or "",
            "description": r[5] or "",
        })
    return persons


# ── Checkpoint ──

def load_checkpoint(filepath: Path) -> dict[int, str]:
    """Load already-classified IDs from JSONL checkpoint."""
    classified = {}
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "id" in obj and "domain" in obj:
                        classified[obj["id"]] = obj["domain"]
                except json.JSONDecodeError:
                    continue
    return classified


def append_checkpoint(filepath: Path, data: dict):
    """Append a result to JSONL checkpoint."""
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


# ── API call ──

async def classify_batch(batch: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """Classify a batch of persons into domains."""
    lines = []
    for i, p in enumerate(batch, 1):
        desc = p["description"][:100] if p["description"] else ""
        role = p["role"] if p["role"] and p["role"] != "occupation" else ""
        info_parts = [f"[ID:{p['id']}] {p['name']}"]
        if p["dates"]:
            info_parts.append(f"({p['dates']})")
        if role:
            info_parts.append(f"- {role}")
        if desc:
            info_parts.append(f"| {desc}")
        lines.append(f"{i}. {' '.join(info_parts)}")

    persons_block = "\n".join(lines)
    prompt = CLASSIFY_PROMPT.format(
        domain_list=DOMAIN_LIST_STR,
        persons_block=persons_block
    )

    async with semaphore:
        try:
            response = await aclient.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=4000,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            results = json.loads(content)

            output = []
            for i, p in enumerate(batch):
                if i < len(results):
                    r = results[i]
                    domain = r.get("domain", "")
                    # Validate domain
                    if domain not in DOMAINS:
                        domain = "entertainment"  # fallback
                    output.append({
                        "id": p["id"],
                        "name": p["name"],
                        "domain": domain,
                    })
                else:
                    output.append({
                        "id": p["id"],
                        "name": p["name"],
                        "domain": "entertainment",
                        "error": "missing from response",
                    })
            return output
        except Exception as e:
            return [
                {"id": p["id"], "name": p["name"], "domain": "", "error": str(e)}
                for p in batch
            ]


# ── Main runner ──

async def run_classification(limit: int = 0):
    """Classify all persons."""
    checkpoint_path = CHECKPOINT_DIR / "persons_domains.jsonl"
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading persons from DB...")
    persons = load_persons(limit)
    print(f"Total persons: {len(persons)}")

    classified = load_checkpoint(checkpoint_path)
    remaining = [p for p in persons if p["id"] not in classified]
    print(f"Already classified: {len(classified)}, remaining: {len(remaining)}")

    if not remaining:
        print("All persons already classified!")
        return

    # Create batches
    batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    print(f"Batches to process: {len(batches)} ({BATCH_SIZE} persons each)")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    start_time = time.time()
    completed = 0
    errors = 0

    # Process in chunks of 50 batches for progress
    chunk_size = 50
    for chunk_start in range(0, len(batches), chunk_size):
        chunk = batches[chunk_start:chunk_start + chunk_size]
        tasks = [classify_batch(batch, semaphore) for batch in chunk]
        batch_results = await asyncio.gather(*tasks)

        for batch_result in batch_results:
            for result in batch_result:
                append_checkpoint(checkpoint_path, result)
                if result.get("domain") and not result.get("error"):
                    completed += 1
                else:
                    errors += 1

        total_batches_done = chunk_start + len(chunk)
        total_done = min(total_batches_done * BATCH_SIZE, len(remaining))
        elapsed = time.time() - start_time
        rate = total_done / elapsed if elapsed > 0 else 0
        eta = (len(remaining) - total_done) / rate if rate > 0 else 0
        print(f"  [{total_done}/{len(remaining)}] "
              f"ok={completed} err={errors} "
              f"rate={rate:.1f}/s ETA={eta/60:.0f}min")

    elapsed = time.time() - start_time
    print(f"\nDone! {completed} classified, {errors} errors in {elapsed:.0f}s")
    print(f"Results: {checkpoint_path}")


def show_stats():
    """Show domain distribution from checkpoint."""
    checkpoint_path = CHECKPOINT_DIR / "persons_domains.jsonl"
    classified = load_checkpoint(checkpoint_path)

    if not classified:
        print("No classification data found!")
        return

    from collections import Counter
    dist = Counter(classified.values())

    print(f"\nDomain Distribution ({len(classified)} persons)")
    print(f"{'='*70}")
    print(f"{'Domain':<16} {'Name (EN)':<28} {'Count':>7} {'%':>6}")
    print(f"{'-'*70}")

    for domain_id in sorted(dist.keys(), key=lambda d: -dist[d]):
        d = DOMAINS.get(domain_id, {"name_en": "?", "global_weight": 0})
        count = dist[domain_id]
        pct = count / len(classified) * 100
        weight = d.get("global_weight", 0)
        print(f"  {domain_id:<16} {d['name_en']:<28} {count:>7} {pct:>5.1f}%  (w={weight})")

    print(f"{'-'*70}")
    print(f"  {'TOTAL':<16} {'':28} {len(classified):>7} 100.0%")


async def main():
    parser = argparse.ArgumentParser(description="Classify persons into historical domains")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of persons (0=all)")
    parser.add_argument("--stats", action="store_true", help="Show domain stats only")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print(f"Model: {MODEL}")
    print(f"Concurrency: {MAX_CONCURRENT}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Domains: {len(DOMAINS)}")
    print()

    # Print domain summary
    print("Domain Taxonomy:")
    for did in sorted(DOMAINS.keys()):
        d = DOMAINS[did]
        print(f"  {did:<16} {d['name_ko']:<12} (w={d['global_weight']}) — {d['field']}")
    print()

    await run_classification(args.limit)


if __name__ == "__main__":
    asyncio.run(main())
