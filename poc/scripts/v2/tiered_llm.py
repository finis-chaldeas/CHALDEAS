"""
3-Tier LLM Pipeline for CHALDEAS V2.

Tier 1: Local LLM (Ollama) - Free, good for classification and date parsing
Tier 2: gpt-5-mini - Low cost, good for moderate complexity
Tier 3: gpt-5.1-chat - Higher cost, best for complex reasoning

Escalation happens when:
- Tier 1 fails or returns low confidence
- Task complexity exceeds tier capability

BENCHMARK RESULTS (2026-02-01, RTX 3060 6GB):
- Entity Extraction: All local models < 7% - MUST escalate to API
- Nature Classification: mistral:7b = 84.6% - Use locally
- Date Parsing: gemma2:9b = 70.5% - Use locally

RECOMMENDED TASK-MODEL MAPPING:
- entity_extraction: ESCALATE TO API (local models failed)
- nature_classification: mistral:7b-instruct-q4_0 (84.6%)
- date_parsing: gemma2:9b-instruct-q4_0 (70.5%)
- complex tasks: gpt-5-mini or gpt-5.1-chat
"""
import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import re

import requests
from dotenv import load_dotenv

load_dotenv()


class LLMTier(Enum):
    LOCAL = 1      # llama3.1 via Ollama
    MINI = 2       # gpt-5-mini
    ADVANCED = 3   # gpt-5.1-chat


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    tier: LLMTier
    confidence: float
    tokens_used: int
    cost: float
    cached: bool = False
    error: Optional[str] = None


@dataclass
class TaskConfig:
    """Configuration for a task type."""
    name: str
    min_tier: LLMTier
    max_tier: LLMTier
    system_prompt: str
    confidence_threshold: float = 0.7
    max_retries: int = 2


class LLMCache:
    """Simple file-based cache for LLM responses."""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'llm_cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_key(self, prompt: str, tier: LLMTier) -> str:
        """Generate cache key from prompt and tier."""
        content = f"{tier.name}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, tier: LLMTier) -> Optional[Dict]:
        """Get cached response."""
        key = self._get_key(prompt, tier)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")

        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def set(self, prompt: str, tier: LLMTier, response: Dict):
        """Cache response."""
        key = self._get_key(prompt, tier)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'prompt_hash': key,
                'tier': tier.name,
                'response': response,
                'cached_at': datetime.now().isoformat()
            }, f, ensure_ascii=False)


class TieredLLM:
    """3-Tier LLM system with automatic escalation."""

    # Cost per 1K tokens (approximate)
    COSTS = {
        LLMTier.LOCAL: 0.0,
        LLMTier.MINI: 0.00025,    # $0.25 per 1M tokens
        LLMTier.ADVANCED: 0.00125  # $1.25 per 1M tokens
    }

    # Task-specific local model overrides (based on benchmark 2026-02-01)
    # Format: task_name -> (model_name, benchmark_accuracy)
    TASK_LOCAL_MODELS = {
        'entity_extraction': None,  # No local model - MUST use API (all < 7%)
        'nature_classification': ('mistral:7b-instruct-q4_0', 0.846),  # Best: 84.6%
        'date_parsing': ('gemma2:9b-instruct-q4_0', 0.705),  # Best: 70.5%
    }

    # Default task configurations
    TASK_CONFIGS = {
        'entity_extraction': TaskConfig(
            name='entity_extraction',
            min_tier=LLMTier.MINI,  # CHANGED: Skip local, go straight to API
            max_tier=LLMTier.ADVANCED,
            system_prompt="You are an expert at extracting named entities from historical texts. Extract persons, locations, and events mentioned in the text. Return valid JSON only.",
            confidence_threshold=0.7
        ),
        'nature_classification': TaskConfig(
            name='nature_classification',
            min_tier=LLMTier.LOCAL,  # Use local mistral:7b (84.6% accuracy)
            max_tier=LLMTier.MINI,
            system_prompt="You are an expert at classifying historical events by their nature. Classify events as: war, battle, treaty, revolution, coronation, death, birth, discovery, founding, migration, cultural_event, natural_disaster, or other. Return ONLY the classification word.",
            confidence_threshold=0.8
        ),
        'date_parsing': TaskConfig(
            name='date_parsing',
            min_tier=LLMTier.LOCAL,  # Use local gemma2:9b (70.5% accuracy)
            max_tier=LLMTier.MINI,
            system_prompt="You are an expert at parsing historical dates. Convert date strings to structured format with year, month, day, and precision. Return valid JSON only.",
            confidence_threshold=0.7
        ),
        'description_generation': TaskConfig(
            name='description_generation',
            min_tier=LLMTier.MINI,
            max_tier=LLMTier.ADVANCED,
            system_prompt="You are a historian writing accurate, engaging descriptions of historical events. Use facts and maintain academic tone.",
            confidence_threshold=0.7
        ),
        'relationship_inference': TaskConfig(
            name='relationship_inference',
            min_tier=LLMTier.MINI,
            max_tier=LLMTier.ADVANCED,
            system_prompt="You are an expert at identifying causal and temporal relationships between historical events. Identify how events are connected.",
            confidence_threshold=0.6
        ),
        'complex_analysis': TaskConfig(
            name='complex_analysis',
            min_tier=LLMTier.ADVANCED,
            max_tier=LLMTier.ADVANCED,
            system_prompt="You are a senior historian performing complex analysis of historical patterns and relationships.",
            confidence_threshold=0.8
        )
    }

    def __init__(self, use_cache: bool = True, cost_tracker=None):
        self.cache = LLMCache() if use_cache else None
        self.cost_tracker = cost_tracker

        # API settings
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.default_ollama_model = os.getenv('OLLAMA_MODEL', 'gemma2:9b-instruct-q4_0')  # Best overall
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Current task context (for model selection)
        self._current_task = None

        # Statistics
        self.stats = {
            'calls': {tier: 0 for tier in LLMTier},
            'tokens': {tier: 0 for tier in LLMTier},
            'cost': {tier: 0.0 for tier in LLMTier},
            'cache_hits': 0,
            'escalations': 0,
            'models_used': {}  # Track which model was used for each task
        }

    def _get_local_model_for_task(self, task: str) -> Optional[str]:
        """Get the optimal local model for a specific task."""
        if task in self.TASK_LOCAL_MODELS:
            model_info = self.TASK_LOCAL_MODELS[task]
            if model_info is not None:
                return model_info[0]  # Return model name
        return self.default_ollama_model

    def process(self, task: str, prompt: str, context: Dict = None,
                force_tier: LLMTier = None) -> LLMResponse:
        """
        Process a task with automatic tier selection and escalation.

        Args:
            task: Task type (e.g., 'entity_extraction')
            prompt: The actual prompt to send
            context: Additional context for the task
            force_tier: Force a specific tier (skip escalation)

        Returns:
            LLMResponse with result
        """
        # Set current task for model selection
        self._current_task = task

        config = self.TASK_CONFIGS.get(task)
        if not config:
            config = TaskConfig(
                name=task,
                min_tier=LLMTier.LOCAL,
                max_tier=LLMTier.ADVANCED,
                system_prompt="You are a helpful assistant.",
                confidence_threshold=0.5
            )

        # Check if local model is available for this task
        local_model = self._get_local_model_for_task(task)
        if local_model is None and config.min_tier == LLMTier.LOCAL:
            # No local model for this task, skip to MINI
            config = TaskConfig(
                name=config.name,
                min_tier=LLMTier.MINI,
                max_tier=config.max_tier,
                system_prompt=config.system_prompt,
                confidence_threshold=config.confidence_threshold
            )

        # Determine starting tier
        current_tier = force_tier or config.min_tier

        # Try each tier until success or max tier reached
        while True:
            # Check cache first
            if self.cache:
                cached = self.cache.get(prompt, current_tier)
                if cached:
                    self.stats['cache_hits'] += 1
                    return LLMResponse(
                        content=cached['response'].get('content', ''),
                        tier=current_tier,
                        confidence=cached['response'].get('confidence', 1.0),
                        tokens_used=0,
                        cost=0.0,
                        cached=True
                    )

            # Make API call
            response = self._call_tier(current_tier, prompt, config.system_prompt)

            if response.error is None and response.confidence >= config.confidence_threshold:
                # Success - cache and return
                if self.cache:
                    self.cache.set(prompt, current_tier, {
                        'content': response.content,
                        'confidence': response.confidence
                    })

                # Track cost
                if self.cost_tracker:
                    self.cost_tracker.record_call(current_tier, response.tokens_used, response.cost)

                return response

            # Check if we can escalate
            if current_tier.value >= config.max_tier.value or force_tier:
                # Can't escalate further, return what we have
                return response

            # Escalate to next tier
            self.stats['escalations'] += 1
            current_tier = LLMTier(current_tier.value + 1)
            print(f"    Escalating to Tier {current_tier.value}...")

    def _call_tier(self, tier: LLMTier, prompt: str, system_prompt: str) -> LLMResponse:
        """Call the appropriate API for the given tier."""
        self.stats['calls'][tier] += 1

        if tier == LLMTier.LOCAL:
            return self._call_ollama(prompt, system_prompt)
        else:
            return self._call_openai(tier, prompt, system_prompt)

    def _call_ollama(self, prompt: str, system_prompt: str) -> LLMResponse:
        """Call local Ollama API with task-specific model."""
        # Get optimal model for current task
        model = self._get_local_model_for_task(self._current_task)

        # Track model usage
        if model not in self.stats['models_used']:
            self.stats['models_used'][model] = 0
        self.stats['models_used'][model] += 1

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                },
                timeout=120  # Increased timeout for larger models like gemma2
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get('response', '')
                tokens = data.get('eval_count', 0) + data.get('prompt_eval_count', 0)

                self.stats['tokens'][LLMTier.LOCAL] += tokens

                # Estimate confidence based on response quality
                confidence = self._estimate_confidence(content, prompt)

                return LLMResponse(
                    content=content,
                    tier=LLMTier.LOCAL,
                    confidence=confidence,
                    tokens_used=tokens,
                    cost=0.0
                )
            else:
                return LLMResponse(
                    content='',
                    tier=LLMTier.LOCAL,
                    confidence=0.0,
                    tokens_used=0,
                    cost=0.0,
                    error=f"Ollama error: {response.status_code}"
                )

        except Exception as e:
            return LLMResponse(
                content='',
                tier=LLMTier.LOCAL,
                confidence=0.0,
                tokens_used=0,
                cost=0.0,
                error=str(e)
            )

    def _call_openai(self, tier: LLMTier, prompt: str, system_prompt: str) -> LLMResponse:
        """Call OpenAI API."""
        if not self.openai_api_key:
            return LLMResponse(
                content='',
                tier=tier,
                confidence=0.0,
                tokens_used=0,
                cost=0.0,
                error="OpenAI API key not configured"
            )

        model = "gpt-5-mini" if tier == LLMTier.MINI else "gpt-5.1-chat"

        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens

            self.stats['tokens'][tier] += tokens
            cost = tokens * self.COSTS[tier] / 1000
            self.stats['cost'][tier] += cost

            confidence = self._estimate_confidence(content, prompt)

            return LLMResponse(
                content=content,
                tier=tier,
                confidence=confidence,
                tokens_used=tokens,
                cost=cost
            )

        except Exception as e:
            return LLMResponse(
                content='',
                tier=tier,
                confidence=0.0,
                tokens_used=0,
                cost=0.0,
                error=str(e)
            )

    def _estimate_confidence(self, response: str, prompt: str) -> float:
        """Estimate confidence based on response quality."""
        if not response:
            return 0.0

        confidence = 0.5  # Base confidence

        # Check if response contains expected patterns
        if 'json' in prompt.lower():
            # Expecting JSON response
            if re.search(r'\{[^{}]+\}', response):
                confidence += 0.3
            try:
                json.loads(response)
                confidence += 0.2
            except:
                pass

        # Check response length
        if len(response) > 50:
            confidence += 0.1

        # Check for error indicators
        if any(err in response.lower() for err in ['error', 'unable', 'cannot', 'don\'t know']):
            confidence -= 0.3

        return min(1.0, max(0.0, confidence))

    def batch_process(self, tasks: List[Tuple[str, str, Dict]]) -> List[LLMResponse]:
        """
        Process multiple tasks in batch.

        Args:
            tasks: List of (task_type, prompt, context) tuples

        Returns:
            List of LLMResponse objects
        """
        results = []
        for task_type, prompt, context in tasks:
            result = self.process(task_type, prompt, context)
            results.append(result)
        return results

    def get_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            'calls': {tier.name: count for tier, count in self.stats['calls'].items()},
            'tokens': {tier.name: count for tier, count in self.stats['tokens'].items()},
            'cost': {tier.name: f"${cost:.4f}" for tier, cost in self.stats['cost'].items()},
            'total_cost': f"${sum(self.stats['cost'].values()):.4f}",
            'cache_hits': self.stats['cache_hits'],
            'escalations': self.stats['escalations']
        }

    def print_stats(self):
        """Print usage statistics."""
        stats = self.get_stats()
        print("\nLLM Usage Statistics:")
        print("=" * 40)
        for tier in LLMTier:
            print(f"  {tier.name}:")
            print(f"    Calls: {stats['calls'][tier.name]}")
            print(f"    Tokens: {stats['tokens'][tier.name]}")
            print(f"    Cost: {stats['cost'][tier.name]}")
        print("-" * 40)
        print(f"  Total Cost: {stats['total_cost']}")
        print(f"  Cache Hits: {stats['cache_hits']}")
        print(f"  Escalations: {stats['escalations']}")
        if self.stats['models_used']:
            print("\n  Local Models Used:")
            for model, count in self.stats['models_used'].items():
                print(f"    {model}: {count} calls")


# Convenience function for simple usage
def process_with_llm(task: str, prompt: str, **kwargs) -> str:
    """Simple function to process a prompt with the tiered LLM system."""
    llm = TieredLLM()
    response = llm.process(task, prompt, **kwargs)
    return response.content


if __name__ == '__main__':
    # Test the pipeline
    print("Testing TieredLLM Pipeline with Task-Specific Models...")
    print("=" * 60)

    llm = TieredLLM(use_cache=False)  # Disable cache for testing

    # Test entity extraction (should escalate to API since local failed in benchmark)
    print("\n1. Testing entity extraction...")
    print("   Expected: Escalate to API (local models < 7% in benchmark)")
    response = llm.process(
        'entity_extraction',
        'Extract entities from: Alexander the Great conquered Persia in 334 BCE.'
    )
    print(f"   Tier used: {response.tier.name}")
    print(f"   Response: {response.content[:100] if response.content else 'N/A'}...")

    # Test nature classification (should use mistral:7b locally)
    print("\n2. Testing nature classification...")
    print("   Expected: LOCAL with mistral:7b-instruct-q4_0 (84.6% benchmark)")
    response = llm.process(
        'nature_classification',
        'Classify: The Siege of Constantinople in 1453 when the Ottoman Empire captured the Byzantine capital.'
    )
    print(f"   Tier used: {response.tier.name}")
    print(f"   Response: {response.content}")

    # Test date parsing (should use gemma2:9b locally)
    print("\n3. Testing date parsing...")
    print("   Expected: LOCAL with gemma2:9b-instruct-q4_0 (70.5% benchmark)")
    response = llm.process(
        'date_parsing',
        'Parse this date: "15 March 44 BCE"'
    )
    print(f"   Tier used: {response.tier.name}")
    print(f"   Response: {response.content}")

    # Print stats
    llm.print_stats()

    print("\n" + "=" * 60)
    print("TASK-MODEL MAPPING (from benchmark 2026-02-01):")
    print("-" * 60)
    for task, model_info in TieredLLM.TASK_LOCAL_MODELS.items():
        if model_info:
            print(f"  {task}: {model_info[0]} ({model_info[1]*100:.1f}%)")
        else:
            print(f"  {task}: ESCALATE TO API (local models failed)")
