"""
Local LLM Benchmark for CHALDEAS.

Tests llama3.1 accuracy on:
1. Entity extraction
2. Nature classification
3. Date parsing

Usage:
    python local_llm_benchmark.py          # Run full benchmark
    python local_llm_benchmark.py --dry-run  # Test without LLM calls
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v2'))

from work_logger import WorkLogger

# Ollama settings (can be overridden by command line)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b-instruct-q4_0')  # Default


class LocalLLMBenchmark:
    """Benchmark local LLM performance."""

    def __init__(self, dry_run: bool = False, model: str = None):
        self.dry_run = dry_run
        self.model = model or OLLAMA_MODEL
        self.results = {
            'entity_extraction': [],
            'nature_classification': [],
            'date_parsing': []
        }
        self.metrics = {}

    def load_golden_dataset(self) -> Dict:
        """Load the golden dataset."""
        dataset_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'benchmark', 'golden_dataset.json'
        )
        with open(dataset_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def call_ollama(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Call Ollama API."""
        if self.dry_run:
            return '{"mock": "response"}'

        try:
            import requests
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt or "You are a helpful assistant for historical data extraction.",
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                print(f"    Ollama error: {response.status_code}")
                return None
        except Exception as e:
            print(f"    Ollama connection error: {e}")
            return None

    def test_entity_extraction(self, sample: Dict) -> Dict:
        """Test entity extraction accuracy."""
        prompt = f"""Extract named entities from the following historical text.
Return a JSON object with these keys:
- persons: list of person names mentioned
- locations: list of location names mentioned
- events: list of event names if any

Text: {sample['input']['text']}

Context: {sample['input'].get('context', '')}

Return ONLY valid JSON, no explanation."""

        response = self.call_ollama(prompt)

        if self.dry_run:
            # Mock successful extraction
            extracted = sample['expected_output']
        else:
            try:
                # Try to parse JSON from response
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                else:
                    extracted = {'persons': [], 'locations': [], 'events': []}
            except:
                extracted = {'persons': [], 'locations': [], 'events': []}

        # Calculate accuracy
        expected_persons = set(sample['expected_output'].get('persons', []))
        extracted_persons = set(extracted.get('persons', []))

        if expected_persons:
            # Fuzzy matching for names
            matches = sum(1 for ep in expected_persons
                         if any(ep.lower() in xp.lower() or xp.lower() in ep.lower()
                               for xp in extracted_persons))
            precision = matches / len(extracted_persons) if extracted_persons else 0
            recall = matches / len(expected_persons)
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        else:
            f1 = 1.0 if not extracted_persons else 0

        return {
            'sample_id': sample['id'],
            'expected': sample['expected_output'],
            'extracted': extracted,
            'f1_score': f1,
            'success': f1 >= 0.5
        }

    def test_nature_classification(self, sample: Dict) -> Dict:
        """Test event nature classification accuracy."""
        prompt = f"""Classify the nature of this historical event.

Title: {sample['input']['title']}
Description: {sample['input'].get('description', 'N/A')}
Date: {sample['input'].get('date', 'Unknown')}

Choose ONE from: war, battle, treaty, revolution, coronation, death, birth, discovery, founding, migration, cultural_event, natural_disaster, other

Return ONLY the classification word, nothing else."""

        response = self.call_ollama(prompt)

        if self.dry_run:
            predicted = sample['expected_output']['nature']
        else:
            # Extract classification from response
            response_lower = response.lower().strip() if response else ''
            valid_natures = ['war', 'battle', 'treaty', 'revolution', 'coronation',
                           'death', 'birth', 'discovery', 'founding', 'migration',
                           'cultural_event', 'natural_disaster', 'other']
            predicted = next((n for n in valid_natures if n in response_lower), 'other')

        expected = sample['expected_output']['nature']
        correct = predicted == expected

        return {
            'sample_id': sample['id'],
            'expected': expected,
            'predicted': predicted,
            'correct': correct
        }

    def test_date_parsing(self, sample: Dict) -> Dict:
        """Test date parsing accuracy."""
        prompt = f"""Parse this date string into structured format.

Date string: {sample['input']['date_string']}

Return a JSON object with these keys (use null for unknown):
- year: integer (negative for BCE)
- month: integer 1-12
- day: integer 1-31
- precision: one of "exact", "month", "year", "decade", "century", "approximate", "range", "era"
- year_start: for ranges
- year_end: for ranges

Return ONLY valid JSON, no explanation."""

        response = self.call_ollama(prompt)

        if self.dry_run:
            parsed = sample['expected_output']
        else:
            try:
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                else:
                    parsed = {}
            except:
                parsed = {}

        expected = sample['expected_output']

        # Calculate score based on key fields
        score = 0
        total = 0

        # Year accuracy (most important)
        if 'year' in expected:
            total += 2
            if parsed.get('year') == expected['year']:
                score += 2
            elif parsed.get('year') and abs(parsed.get('year', 0) - expected['year']) <= 10:
                score += 1

        # Precision accuracy
        if 'precision' in expected:
            total += 1
            if parsed.get('precision') == expected['precision']:
                score += 1

        # Month/day accuracy
        for field in ['month', 'day']:
            if field in expected and expected[field] is not None:
                total += 0.5
                if parsed.get(field) == expected[field]:
                    score += 0.5

        accuracy = score / total if total > 0 else 0

        return {
            'sample_id': sample['id'],
            'input': sample['input']['date_string'],
            'expected': expected,
            'parsed': parsed,
            'accuracy': accuracy,
            'success': accuracy >= 0.7
        }

    def run_benchmark(self) -> Dict:
        """Run the full benchmark."""
        dataset = self.load_golden_dataset()

        print(f"\nRunning benchmark on {dataset['total_samples']} samples...")
        print(f"Model: {self.model}")
        print(f"Dry run: {self.dry_run}")
        print("=" * 50)

        for sample in dataset['samples']:
            task = sample['task']
            print(f"  Testing {sample['id']}...", end=' ')

            if task == 'entity_extraction':
                result = self.test_entity_extraction(sample)
                self.results['entity_extraction'].append(result)
                print(f"F1={result['f1_score']:.2f}")

            elif task == 'nature_classification':
                result = self.test_nature_classification(sample)
                self.results['nature_classification'].append(result)
                status = 'OK' if result['correct'] else 'FAIL'
                print(f"{status} (expected={result['expected']}, got={result['predicted']})")

            elif task == 'date_parsing':
                result = self.test_date_parsing(sample)
                self.results['date_parsing'].append(result)
                print(f"Accuracy={result['accuracy']:.2f}")

        # Calculate metrics
        self.calculate_metrics()
        return self.metrics

    def calculate_metrics(self):
        """Calculate overall metrics."""
        # Entity extraction
        entity_results = self.results['entity_extraction']
        if entity_results:
            avg_f1 = sum(r['f1_score'] for r in entity_results) / len(entity_results)
            success_rate = sum(1 for r in entity_results if r['success']) / len(entity_results)
            self.metrics['entity_extraction'] = {
                'count': len(entity_results),
                'avg_f1': avg_f1,
                'success_rate': success_rate
            }

        # Nature classification
        nature_results = self.results['nature_classification']
        if nature_results:
            accuracy = sum(1 for r in nature_results if r['correct']) / len(nature_results)
            self.metrics['nature_classification'] = {
                'count': len(nature_results),
                'accuracy': accuracy
            }

        # Date parsing
        date_results = self.results['date_parsing']
        if date_results:
            avg_accuracy = sum(r['accuracy'] for r in date_results) / len(date_results)
            success_rate = sum(1 for r in date_results if r['success']) / len(date_results)
            self.metrics['date_parsing'] = {
                'count': len(date_results),
                'avg_accuracy': avg_accuracy,
                'success_rate': success_rate
            }

        # Overall
        total_success = (
            sum(1 for r in entity_results if r['success']) +
            sum(1 for r in nature_results if r['correct']) +
            sum(1 for r in date_results if r['success'])
        )
        total_samples = len(entity_results) + len(nature_results) + len(date_results)

        self.metrics['overall'] = {
            'total_samples': total_samples,
            'total_success': total_success,
            'overall_accuracy': total_success / total_samples if total_samples > 0 else 0
        }

    def save_results(self, output_path: str = None):
        """Save benchmark results to file."""
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'benchmark',
                f'benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )

        report = {
            'timestamp': datetime.now().isoformat(),
            'model': self.model,
            'dry_run': self.dry_run,
            'metrics': self.metrics,
            'detailed_results': self.results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {output_path}")
        return output_path

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 50)
        print("BENCHMARK SUMMARY")
        print("=" * 50)

        if 'entity_extraction' in self.metrics:
            m = self.metrics['entity_extraction']
            print(f"\nEntity Extraction ({m['count']} samples):")
            print(f"  Average F1 Score: {m['avg_f1']:.2%}")
            print(f"  Success Rate (F1 >= 0.5): {m['success_rate']:.2%}")

        if 'nature_classification' in self.metrics:
            m = self.metrics['nature_classification']
            print(f"\nNature Classification ({m['count']} samples):")
            print(f"  Accuracy: {m['accuracy']:.2%}")

        if 'date_parsing' in self.metrics:
            m = self.metrics['date_parsing']
            print(f"\nDate Parsing ({m['count']} samples):")
            print(f"  Average Accuracy: {m['avg_accuracy']:.2%}")
            print(f"  Success Rate (>= 70%): {m['success_rate']:.2%}")

        if 'overall' in self.metrics:
            m = self.metrics['overall']
            print(f"\n{'='*50}")
            print(f"OVERALL: {m['overall_accuracy']:.2%} accuracy")
            print(f"({m['total_success']}/{m['total_samples']} successful)")
            print("=" * 50)


def main():
    global OLLAMA_MODEL
    parser = argparse.ArgumentParser(description='Local LLM Benchmark')
    parser.add_argument('--dry-run', action='store_true', help='Test without LLM calls')
    parser.add_argument('--model', type=str, default=OLLAMA_MODEL, help='Ollama model to use')
    args = parser.parse_args()

    OLLAMA_MODEL = args.model

    with WorkLogger('CP-2.1', f'Local LLM Benchmark ({args.model})') as log:
        benchmark = LocalLLMBenchmark(dry_run=args.dry_run, model=args.model)

        try:
            metrics = benchmark.run_benchmark()
            benchmark.print_summary()
            benchmark.save_results()

            log.record_progress(processed=metrics['overall']['total_samples'])
            log.add_note(f"Overall accuracy: {metrics['overall']['overall_accuracy']:.2%}")

            if not args.dry_run:
                log.record_llm_call(tier=1)  # Local LLM = tier 1

        except FileNotFoundError:
            print("Golden dataset not found. Run create_golden_dataset.py first.")
            log.add_note("Failed: Golden dataset not found")
            raise


if __name__ == '__main__':
    main()
