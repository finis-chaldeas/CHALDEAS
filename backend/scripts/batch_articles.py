"""
Batch generate portal articles.

Usage:
    cd backend
    PYTHONIOENCODING=utf-8 python scripts/batch_articles.py
    PYTHONIOENCODING=utf-8 python scripts/batch_articles.py --dry-run
    PYTHONIOENCODING=utf-8 python scripts/batch_articles.py --start 5  # skip first 4
"""
import subprocess
import sys
import time

# 30 topics (English for better GPT quality + DB event matching)
TOPICS = [
    # Ancient
    ("Battle of Marathon and the Birth of Democracy", "history", "ancient-warfare"),
    ("Thermopylae — 300 Spartans and the Price of Sacrifice", "history", "ancient-warfare"),
    ("Alexander the Great's Eastern Campaign", "history", "ancient-empires"),
    ("Hannibal Crosses the Alps — The Punic Wars", "history", "ancient-warfare"),
    ("Caesar and the Rubicon — End of the Roman Republic", "history", "ancient-politics"),
    ("Cleopatra and the Fall of Ptolemaic Egypt", "history", "ancient-politics"),
    ("Rise and Fall of the Roman Empire", "history", "ancient-empires"),
    ("Qin Shi Huang and the Unification of China", "history", "ancient-empires"),
    ("The Persian Empire — From Cyrus to Darius", "history", "ancient-empires"),
    ("The Battle of Salamis — How Athens Saved Greece", "history", "ancient-warfare"),
    # Medieval
    ("The Crusades — Holy War and Its Consequences", "history", "medieval-warfare"),
    ("The Viking Age — Raiders, Traders, and Explorers", "history", "medieval-expansion"),
    ("The Byzantine Empire — A Thousand Years of Rome's Successor", "history", "medieval-empires"),
    ("The Hundred Years' War and Joan of Arc", "history", "medieval-warfare"),
    ("The Reconquista — 800 Years to Reclaim Iberia", "history", "medieval-warfare"),
    ("Rise of the Ottoman Empire", "history", "medieval-empires"),
    # Early Modern
    ("The Age of Exploration — When Europe Discovered the World", "history", "early-modern"),
    ("The Renaissance — Rebirth of Art, Science, and Ideas", "history", "early-modern"),
    ("The Reformation — How Martin Luther Split Christianity", "history", "early-modern"),
    ("The Thirty Years' War — Europe's Deadliest Conflict", "history", "early-modern-warfare"),
    ("Fall of the Ming Dynasty", "history", "east-asian-empires"),
    # Modern
    ("The French Revolution — Liberty, Equality, and Terror", "history", "modern-revolutions"),
    ("The Industrial Revolution — How Machines Changed Everything", "history", "modern-transformation"),
    ("The American Revolution — Birth of a Nation", "history", "modern-revolutions"),
    ("The Meiji Restoration — Japan's Leap into Modernity", "history", "modern-transformation"),
    # Contemporary
    ("World War I — The War That Ended All Certainties", "history", "world-wars"),
    ("World War II — The Conflict That Shaped Our World", "history", "world-wars"),
    ("The Cold War — When the World Held Its Breath", "history", "cold-war"),
    # Essays
    ("From Phalanx to Gunpowder — The Evolution of Warfare", "essay", "warfare-evolution"),
    ("When Plagues Changed History — Pandemics as Turning Points", "essay", "historical-patterns"),
]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start", type=int, default=0, help="Start from topic index (0-based)")
    parser.add_argument("--limit", type=int, default=999, help="Max articles to generate")
    parser.add_argument("--model", type=str, default="gpt-5.2", help="Outline model")
    args = parser.parse_args()

    topics = TOPICS[args.start:args.start + args.limit]

    print(f"=== Batch Article Generation ===")
    print(f"  Topics: {len(topics)} (from index {args.start})")
    print(f"  Model: {args.model}")
    if args.dry_run:
        print(f"  Mode: DRY RUN")
    print()

    total_cost = 0.0
    success = 0
    failed = []

    for i, (topic, item_type, theme) in enumerate(topics):
        idx = args.start + i
        print(f"\n{'='*60}")
        print(f"  [{idx+1}/{len(TOPICS)}] {topic}")
        print(f"  Type: {item_type}, Theme: {theme}")
        print(f"{'='*60}")

        if args.dry_run:
            print(f"  (skipped — dry run)")
            continue

        t_start = time.time()
        try:
            result = subprocess.run(
                [
                    sys.executable, "scripts/create_portal_article.py",
                    "--generate", topic,
                    "--type", item_type,
                    "--theme", theme,
                    "--model", args.model,
                ],
                capture_output=True, text=True, encoding='utf-8',
                timeout=300,  # 5 min per article
                cwd=str(__import__('pathlib').Path(__file__).parent.parent),
                env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"},
            )

            print(result.stdout)
            if result.stderr:
                print(f"  STDERR: {result.stderr[:200]}")

            if result.returncode == 0:
                # Extract cost from output
                for line in result.stdout.split('\n'):
                    if 'Cost:' in line:
                        try:
                            cost_str = line.split('$')[1].strip()
                            total_cost += float(cost_str)
                        except (IndexError, ValueError):
                            pass
                success += 1
            else:
                failed.append((idx, topic, f"exit code {result.returncode}"))
                print(f"  FAILED (exit code {result.returncode})")

        except subprocess.TimeoutExpired:
            failed.append((idx, topic, "timeout"))
            print(f"  FAILED (timeout)")
        except Exception as e:
            failed.append((idx, topic, str(e)))
            print(f"  FAILED ({e})")

        elapsed = time.time() - t_start
        print(f"  Elapsed: {elapsed:.1f}s")

    print(f"\n{'='*60}")
    print(f"=== Batch Complete ===")
    print(f"  Success: {success}/{len(topics)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Total cost: ~${total_cost:.3f}")
    if failed:
        print(f"\n  Failed topics:")
        for idx, topic, reason in failed:
            print(f"    [{idx}] {topic}: {reason}")


if __name__ == "__main__":
    main()
