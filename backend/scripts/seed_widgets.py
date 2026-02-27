"""Seed test widget data into shift pages.

Inserts sample widgets for famous battles (Marathon, Thermopylae, Salamis)
to verify the widget rendering pipeline.

Usage:
    python scripts/seed_widgets.py             # Apply
    python scripts/seed_widgets.py --dry-run   # Preview only
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.v1.chain import ChainSegment

# Widget seed data: (title_substring, sequence_number, widgets)
SEED_DATA = [
    # Marathon
    ("Marathon", None, [
        {
            "type": "faction_vs",
            "slot": "right",
            "priority": 1,
            "data": {
                "left_name": "Athens",
                "left_name_ko": "아테네",
                "left_commander": "Miltiades",
                "left_commander_ko": "밀티아데스",
                "left_strength": "10,000 hoplites",
                "left_strength_ko": "중장보병 1만",
                "right_name": "Persia",
                "right_name_ko": "페르시아",
                "right_commander": "Datis & Artaphernes",
                "right_commander_ko": "다티스 & 아르타프레네스",
                "right_strength": "25,000 infantry",
                "right_strength_ko": "보병 2만 5천",
                "outcome": "Decisive Athenian victory",
                "outcome_ko": "아테네의 결정적 승리"
            }
        },
        {
            "type": "dramatic_stat",
            "slot": "left",
            "priority": 2,
            "data": {
                "number": "42",
                "suffix": "km",
                "label": "Marathon to Athens",
                "label_ko": "마라톤에서 아테네까지",
                "context": "The distance Pheidippides ran to announce victory",
                "context_ko": "페이디피데스가 승전보를 전하기 위해 달린 거리"
            }
        },
        {
            "type": "person_card",
            "slot": "left",
            "priority": 3,
            "data": {
                "name": "Miltiades",
                "name_ko": "밀티아데스",
                "role": "Strategos of Athens",
                "role_ko": "아테네 전략가",
                "birth_year": -550,
                "death_year": -489,
                "summary": "Convinced the Athenian assembly to meet the Persians at Marathon rather than defend the city. His bold double-envelopment tactic shattered the Persian center.",
                "summary_ko": "아테네 시민회를 설득해 마라톤에서 페르시아를 맞도록 했다. 그의 대담한 양익포위 전술이 페르시아 중앙을 분쇄했다."
            }
        },
        {
            "type": "era_context",
            "slot": "bottom",
            "priority": 5,
            "data": {
                "heading": "Meanwhile in 490 BCE",
                "heading_ko": "그 무렵, 기원전 490년",
                "items": [
                    {
                        "region": "China",
                        "region_ko": "중국",
                        "text": "The Spring and Autumn period nears its end. Confucius is alive, traveling between states teaching his philosophy.",
                        "text_ko": "춘추시대가 막바지에 이른다. 공자가 살아 있으며, 여러 나라를 돌아다니며 자신의 철학을 가르치고 있다."
                    },
                    {
                        "region": "India",
                        "region_ko": "인도",
                        "text": "The Mahajanapadas flourish. The Buddha passed away roughly a decade ago; his teachings are spreading across the subcontinent.",
                        "text_ko": "마하자나파다가 번영한다. 부처가 대략 10년 전 입멸했으며, 그의 가르침이 아대륙 전역으로 퍼지고 있다."
                    },
                    {
                        "region": "Rome",
                        "region_ko": "로마",
                        "text": "The young Roman Republic is only 20 years old, still a minor city-state in central Italy.",
                        "text_ko": "로마 공화국은 겨우 20살. 이탈리아 중부의 소도시 국가에 불과하다."
                    }
                ]
            }
        },
        {
            "type": "battle_stats",
            "slot": "right",
            "priority": 2,
            "data": {
                "heading": "Battle Statistics",
                "heading_ko": "전투 통계",
                "stats": [
                    {"label": "Greek casualties", "label_ko": "그리스 사상자", "value": "~192", "value_ko": "약 192명"},
                    {"label": "Persian casualties", "label_ko": "페르시아 사상자", "value": "~6,400", "value_ko": "약 6,400명"},
                    {"label": "Duration", "label_ko": "기간", "value": "1 day", "value_ko": "1일"},
                    {"label": "Terrain", "label_ko": "지형", "value": "Coastal plain", "value_ko": "해안 평야"}
                ],
                "significance": "First major Greek victory against Persia; proved hoplite phalanx could defeat larger Persian forces",
                "significance_ko": "그리스의 첫 대규모 대페르시아 승리; 중장보병 밀집대형이 대규모 페르시아군을 격파할 수 있음을 증명"
            }
        },
    ]),
    # Thermopylae
    ("Thermopylae", None, [
        {
            "type": "faction_vs",
            "slot": "right",
            "priority": 1,
            "data": {
                "left_name": "Greek Alliance",
                "left_name_ko": "그리스 동맹",
                "left_commander": "Leonidas I",
                "left_commander_ko": "레오니다스 1세",
                "left_strength": "7,000 (300 Spartans)",
                "left_strength_ko": "7,000명 (스파르타 300명)",
                "left_details": ["Sparta", "Thespiae", "Thebes"],
                "left_details_ko": ["스파르타", "테스피아이", "테바이"],
                "right_name": "Persian Empire",
                "right_name_ko": "페르시아 제국",
                "right_commander": "Xerxes I",
                "right_commander_ko": "크세르크세스 1세",
                "right_strength": "70,000\u2013300,000",
                "outcome": "Persian victory, but heavy cost",
                "outcome_ko": "페르시아 승리, 그러나 막대한 대가"
            }
        },
        {
            "type": "primary_quote",
            "slot": "left",
            "priority": 1,
            "data": {
                "text": "Go tell the Spartans, stranger passing by, that here obedient to their laws we lie.",
                "text_ko": "지나가는 나그네여, 스파르타인들에게 전하라. 우리가 그들의 법에 복종하여 여기 누워 있노라고.",
                "source": "Histories",
                "source_ko": "역사",
                "speaker": "Simonides of Ceos",
                "speaker_ko": "케오스의 시모니데스",
                "year": -480
            }
        },
        {
            "type": "person_card",
            "slot": "left",
            "priority": 2,
            "data": {
                "name": "Leonidas I",
                "name_ko": "레오니다스 1세",
                "role": "King of Sparta",
                "role_ko": "스파르타의 왕",
                "birth_year": -540,
                "death_year": -480,
                "summary": "Chose to stay with 300 Spartans at the narrow pass, buying time for Greece to prepare its defense. His sacrifice became the defining symbol of courage against impossible odds.",
                "summary_ko": "좁은 고갯길에 300 스파르타 전사와 함께 남기로 결정하여 그리스가 방어를 준비할 시간을 벌었다. 그의 희생은 불가능한 역경에 맞선 용기의 상징이 되었다."
            }
        },
        {
            "type": "mini_timeline",
            "slot": "left",
            "priority": 3,
            "data": {
                "heading": "Greco-Persian Wars",
                "heading_ko": "그리스-페르시아 전쟁",
                "events": [
                    {"year": -490, "label": "Battle of Marathon", "label_ko": "마라톤 전투"},
                    {"year": -480, "label": "Battle of Thermopylae", "label_ko": "테르모필레 전투", "highlight": True},
                    {"year": -480, "label": "Battle of Salamis", "label_ko": "살라미스 해전"},
                    {"year": -479, "label": "Battle of Plataea", "label_ko": "플라타이아 전투"}
                ]
            }
        },
    ]),
    # Salamis
    ("Salamis", None, [
        {
            "type": "faction_vs",
            "slot": "right",
            "priority": 1,
            "data": {
                "left_name": "Greek Fleet",
                "left_name_ko": "그리스 함대",
                "left_commander": "Themistocles",
                "left_commander_ko": "테미스토클레스",
                "left_strength": "371 triremes",
                "left_strength_ko": "삼단노선 371척",
                "right_name": "Persian Fleet",
                "right_name_ko": "페르시아 함대",
                "right_commander": "Artemisia I",
                "right_commander_ko": "아르테미시아 1세",
                "right_strength": "600\u20131,200 ships",
                "right_strength_ko": "600\u20131,200척",
                "outcome": "Decisive Greek victory, turning point of the war",
                "outcome_ko": "그리스의 결정적 승리, 전쟁의 전환점"
            }
        },
        {
            "type": "dramatic_stat",
            "slot": "left",
            "priority": 1,
            "data": {
                "number": "371",
                "label": "Greek Triremes",
                "label_ko": "그리스 삼단노선",
                "context": "A smaller fleet that used the narrow strait to nullify Persian numbers",
                "context_ko": "좁은 해협을 이용해 페르시아의 수적 우위를 무력화한 소규모 함대"
            }
        },
        {
            "type": "person_card",
            "slot": "left",
            "priority": 2,
            "data": {
                "name": "Themistocles",
                "name_ko": "테미스토클레스",
                "role": "Strategos of Athens",
                "role_ko": "아테네 전략가",
                "birth_year": -524,
                "death_year": -459,
                "summary": "Architect of Athens' naval power. Convinced Athenians to build 200 triremes with silver mine revenue, then lured the Persian fleet into the narrow Strait of Salamis.",
                "summary_ko": "아테네 해군력의 설계자. 은광 수입으로 삼단노선 200척 건조를 시민회에 설득하고, 페르시아 함대를 좁은 살라미스 해협으로 유인했다."
            }
        },
        {
            "type": "era_context",
            "slot": "bottom",
            "priority": 5,
            "data": {
                "heading": "Meanwhile in 480 BCE",
                "heading_ko": "그 무렵, 기원전 480년",
                "items": [
                    {
                        "region": "Carthage",
                        "region_ko": "카르타고",
                        "text": "On the same day as Salamis, Greeks in Sicily defeat Carthage at the Battle of Himera — the Western Mediterranean's own turning point.",
                        "text_ko": "살라미스와 같은 날, 시칠리아의 그리스인들이 히메라 전투에서 카르타고를 격파한다 — 서지중해의 전환점."
                    },
                    {
                        "region": "China",
                        "region_ko": "중국",
                        "text": "Confucius has recently died (479 BCE). The Warring States period is about to begin.",
                        "text_ko": "공자가 최근 사망했다 (기원전 479년). 전국시대가 곧 시작된다."
                    }
                ]
            }
        },
    ]),
]


def seed_widgets(dry_run: bool = False, force: bool = False):
    db = SessionLocal()
    try:
        updated = 0
        skipped = 0

        for title_substr, seq_num, widgets in SEED_DATA:
            # Find matching segments by title substring
            query = db.query(ChainSegment).filter(
                ChainSegment.title.ilike(f"%{title_substr}%")
            )
            if seq_num is not None:
                query = query.filter(ChainSegment.sequence_number == seq_num)

            segments = query.all()

            if not segments:
                print(f"  [SKIP] No segments found matching '{title_substr}'")
                skipped += 1
                continue

            for seg in segments:
                if seg.widgets and not force:
                    print(f"  [SKIP] Segment {seg.id} '{seg.title}' already has widgets")
                    skipped += 1
                    continue

                action = 'DRY' if dry_run else ('UPD' if seg.widgets else 'SET')
                print(f"  [{action}] Segment {seg.id} "
                      f"(chain={seg.chain_id}, seq={seg.sequence_number}) "
                      f"'{seg.title}' <- {len(widgets)} widgets")

                if not dry_run:
                    seg.widgets = widgets
                    updated += 1

        if not dry_run:
            db.commit()

        print(f"\nDone: {updated} updated, {skipped} skipped"
              f"{' (dry run)' if dry_run else ''}")

    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed widget data into shift pages')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--force', action='store_true', help='Overwrite existing widgets')
    args = parser.parse_args()

    seed_widgets(dry_run=args.dry_run, force=args.force)
