# CHALDEAS V2 - Local LLM Benchmark Report

Generated: 2026-02-01 02:03:15

GPU: RTX 3060 (6GB VRAM)

## Summary

| Model | Entity F1 | Nature Acc | Date Acc | Overall | Time |
|-------|-----------|------------|----------|---------|------|
| phi3:mini | 6.5% | 65.4% | 12.6% | 22.6% | 422s |
| mistral:7b-instruct-q4_0 | 0.5% | 84.6% | 47.5% | 33.3% | 405s |
| llama3.1:8b-instruct-q4_0 | 1.8% | 80.8% | 40.2% | 29.0% | 533s |
| qwen3:8b | 0.0% | 69.2% | 46.5% | 34.4% | 3088s |
| gemma2:9b-instruct-q4_0 | 4.4% | 80.8% | 70.5% | 43.0% | 968s |

## Best Models by Task

- **Entity Extraction**: phi3:mini (6.5% F1)
- **Nature Classification**: mistral:7b-instruct-q4_0 (84.6%)
- **Date Parsing**: gemma2:9b-instruct-q4_0 (70.5%)
- **Overall Best**: gemma2:9b-instruct-q4_0 (43.0%)

## Recommendations

| Task | Recommended Model | Tier |
|------|-------------------|------|
| Entity Extraction | phi3:mini | T1 (Local) |
| Nature Classification | mistral:7b-instruct-q4_0 | T1 (Local) |
| Date Parsing | gemma2:9b-instruct-q4_0 | T1 (Local) |
| Complex Analysis | gpt-5-mini / gpt-5.1-chat | T2/T3 (API) |

## Notes

- All tests run on RTX 3060 (6GB VRAM)
- 93 test samples (34 entity, 26 nature, 33 date)
- Cost: $0 (all local models)