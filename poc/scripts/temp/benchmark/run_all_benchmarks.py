"""
Run benchmarks on all available local models.
Generates comparison report.
"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v2'))

import requests
from local_llm_benchmark import LocalLLMBenchmark

OLLAMA_URL = 'http://localhost:11434'

# Models to test (sorted by VRAM usage)
MODELS_TO_TEST = [
    ('phi3:mini', '2.2GB', 'Fast, simple tasks'),
    ('mistral:7b-instruct-q4_0', '4.1GB', 'Good balance'),
    ('llama3.1:8b-instruct-q4_0', '4.7GB', 'General purpose'),
    ('qwen3:8b', '5.2GB', 'High quality, has thinking mode'),
    ('gemma2:9b-instruct-q4_0', '5.4GB', 'Google, good reasoning'),
]


def get_available_models():
    """Get list of models installed in Ollama."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            return [m['name'] for m in response.json().get('models', [])]
    except:
        pass
    return []


def run_single_benchmark(model: str, sample_limit: int = None):
    """Run benchmark for a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"{'='*60}")

    benchmark = LocalLLMBenchmark(dry_run=False, model=model)

    try:
        start_time = time.time()
        metrics = benchmark.run_benchmark()
        elapsed = time.time() - start_time

        # Save individual results
        output_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'benchmark',
            f'benchmark_{model.replace(":", "_").replace("/", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        benchmark.save_results(output_path)

        return {
            'model': model,
            'success': True,
            'elapsed_seconds': elapsed,
            'metrics': metrics,
            'output_file': output_path
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'model': model,
            'success': False,
            'error': str(e)
        }


def generate_comparison_report(results: list):
    """Generate markdown comparison report."""
    report_lines = [
        "# CHALDEAS V2 - Local LLM Benchmark Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\nGPU: RTX 3060 (6GB VRAM)",
        "\n## Summary",
        "\n| Model | Entity F1 | Nature Acc | Date Acc | Overall | Time |",
        "|-------|-----------|------------|----------|---------|------|",
    ]

    for r in results:
        if r['success']:
            m = r['metrics']
            entity_f1 = m.get('entity_extraction', {}).get('avg_f1', 0) * 100
            nature_acc = m.get('nature_classification', {}).get('accuracy', 0) * 100
            date_acc = m.get('date_parsing', {}).get('avg_accuracy', 0) * 100
            overall = m.get('overall', {}).get('overall_accuracy', 0) * 100
            elapsed = f"{r['elapsed_seconds']:.0f}s"

            report_lines.append(
                f"| {r['model']} | {entity_f1:.1f}% | {nature_acc:.1f}% | {date_acc:.1f}% | {overall:.1f}% | {elapsed} |"
            )
        else:
            report_lines.append(f"| {r['model']} | ERROR | - | - | - | - |")

    # Best model per task
    report_lines.extend([
        "\n## Best Models by Task",
        ""
    ])

    successful = [r for r in results if r['success']]
    if successful:
        # Entity extraction
        best_entity = max(successful, key=lambda x: x['metrics'].get('entity_extraction', {}).get('avg_f1', 0))
        report_lines.append(f"- **Entity Extraction**: {best_entity['model']} ({best_entity['metrics']['entity_extraction']['avg_f1']*100:.1f}% F1)")

        # Nature classification
        best_nature = max(successful, key=lambda x: x['metrics'].get('nature_classification', {}).get('accuracy', 0))
        report_lines.append(f"- **Nature Classification**: {best_nature['model']} ({best_nature['metrics']['nature_classification']['accuracy']*100:.1f}%)")

        # Date parsing
        best_date = max(successful, key=lambda x: x['metrics'].get('date_parsing', {}).get('avg_accuracy', 0))
        report_lines.append(f"- **Date Parsing**: {best_date['model']} ({best_date['metrics']['date_parsing']['avg_accuracy']*100:.1f}%)")

        # Overall
        best_overall = max(successful, key=lambda x: x['metrics'].get('overall', {}).get('overall_accuracy', 0))
        report_lines.append(f"- **Overall Best**: {best_overall['model']} ({best_overall['metrics']['overall']['overall_accuracy']*100:.1f}%)")

    # Recommendations
    report_lines.extend([
        "\n## Recommendations",
        "",
        "| Task | Recommended Model | Tier |",
        "|------|-------------------|------|",
    ])

    if successful:
        report_lines.append(f"| Entity Extraction | {best_entity['model']} | T1 (Local) |")
        report_lines.append(f"| Nature Classification | {best_nature['model']} | T1 (Local) |")
        report_lines.append(f"| Date Parsing | {best_date['model']} | T1 (Local) |")
        report_lines.append("| Complex Analysis | gpt-5-mini / gpt-5.1-chat | T2/T3 (API) |")

    report_lines.extend([
        "\n## Notes",
        "",
        "- All tests run on RTX 3060 (6GB VRAM)",
        "- 93 test samples (34 entity, 26 nature, 33 date)",
        "- Cost: $0 (all local models)",
    ])

    return "\n".join(report_lines)


def main():
    print("CHALDEAS V2 - Multi-Model Benchmark")
    print("=" * 60)

    # Check available models
    available = get_available_models()
    print(f"\nInstalled models: {available}")

    # Filter to available models
    models_to_run = [(m, s, d) for m, s, d in MODELS_TO_TEST if m in available]
    print(f"\nWill test {len(models_to_run)} models:")
    for m, s, d in models_to_run:
        print(f"  - {m} ({s}): {d}")

    # Run benchmarks
    results = []
    for model, size, desc in models_to_run:
        result = run_single_benchmark(model)
        results.append(result)

        # Print interim summary
        if result['success']:
            m = result['metrics']
            print(f"\n  Results for {model}:")
            print(f"    Entity F1: {m['entity_extraction']['avg_f1']*100:.1f}%")
            print(f"    Nature Acc: {m['nature_classification']['accuracy']*100:.1f}%")
            print(f"    Date Acc: {m['date_parsing']['avg_accuracy']*100:.1f}%")
            print(f"    Overall: {m['overall']['overall_accuracy']*100:.1f}%")
            print(f"    Time: {result['elapsed_seconds']:.0f}s")

    # Generate report
    report = generate_comparison_report(results)

    # Save report
    report_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'benchmark',
        f'BENCHMARK_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    )
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n\n{'='*60}")
    print("FINAL REPORT")
    print('='*60)
    print(report)
    print(f"\nReport saved to: {report_path}")

    # Save raw results
    results_path = report_path.replace('.md', '.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'models_tested': len(results),
            'results': results
        }, f, indent=2, default=str)


if __name__ == '__main__':
    main()
