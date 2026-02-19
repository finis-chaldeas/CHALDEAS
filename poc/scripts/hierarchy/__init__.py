"""
Event hierarchy classification pipeline.

Modules:
- wikidata_client: Fetch P361 (part of) relationships from Wikidata
- periods: Regional period definitions for auto-classification
- validation: Temporal (±50yr) and spatial validation
- llm_classifier: GPT-5.1 based classification
- unified_classifier: Combined pipeline
"""
from .wikidata_client import WikidataClient, WikidataEvent, EVENT_TYPE_MAPPING
from .periods import Period, PERIODS, find_period_for_event, get_region
from .validation import (
    validate_temporal,
    validate_spatial,
    validate_parent_child,
    can_be_parent,
    ValidationResult,
    ValidationStatus,
    TEMPORAL_TOLERANCE
)
from .llm_classifier import (
    LLMEventClassifier,
    ClassificationResult,
    Confidence,
    build_event_prompt
)
from .unified_classifier import (
    UnifiedClassifier,
    UnifiedResult,
    ClassificationSource,
    run_classification
)

__all__ = [
    # Wikidata
    "WikidataClient",
    "WikidataEvent",
    "EVENT_TYPE_MAPPING",
    # Periods
    "Period",
    "PERIODS",
    "find_period_for_event",
    "get_region",
    # Validation
    "validate_temporal",
    "validate_spatial",
    "validate_parent_child",
    "can_be_parent",
    "ValidationResult",
    "ValidationStatus",
    "TEMPORAL_TOLERANCE",
    # LLM
    "LLMEventClassifier",
    "ClassificationResult",
    "Confidence",
    "build_event_prompt",
    # Unified
    "UnifiedClassifier",
    "UnifiedResult",
    "ClassificationSource",
    "run_classification",
]
