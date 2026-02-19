# Event Hierarchy System Report

> Generated: 2026-01-28

## Overview

CHALDEAS Event Hierarchy System은 46,825개의 역사적 이벤트를 계층적으로 분류하는 시스템입니다.
다중 부모 구조를 지원하며, Wikidata P361, Period 매칭, LLM 분류의 3단계 파이프라인으로 동작합니다.

## Current Status

### Classification Summary

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| **pending** | 15,003 | 32.0% | 부모 찾음, 확인 필요 |
| **unknown** | 31,672 | 67.6% | 미분류 (LLM 필요) |
| **confirmed** | 29 | 0.1% | 확정됨 |
| **none** | 121 | 0.3% | 최상위 이벤트 |

### Wikidata Coverage

- **With Wikidata ID**: 1,571 / 46,825 (3.4%)
- **Wikipedia URLs (processed)**: 1,513
- **Remaining edge cases**: 59 (URL encoding issues)

### Aggregate Events (Parents)

Total: **121 aggregates**

| Type | Count |
|------|-------|
| dynasty | 102 |
| war | 6 |
| (none) | 6 |
| scientific_era | 2 |
| expedition | 2 |
| revolution | 1 |
| philosophical_school | 1 |
| artistic_period | 1 |

### event_parents Table

- **Total Relations**: 15,246
- **Unique Events with Parents**: 15,032
- **Multi-Parent Events**: 214 (1.4%)

### Context Distribution

| Context | Count | Percentage |
|---------|-------|------------|
| dynasty | 12,478 | 81.8% |
| scientific_era | 1,114 | 7.3% |
| philosophical_school | 687 | 4.5% |
| war | 404 | 2.6% |
| expedition | 347 | 2.3% |
| revolution | 153 | 1.0% |
| artistic_period | 61 | 0.4% |
| general | 2 | 0.0% |

### Top 10 Parent Events

| Parent Event | Children | Type |
|--------------|----------|------|
| Modern history | 5,745 | dynasty |
| Early modern period | 1,704 | dynasty |
| Industrial Revolution | 1,113 | scientific_era |
| Classical antiquity | 921 | dynasty |
| Age of Enlightenment | 687 | philosophical_school |
| High Middle Ages | 597 | dynasty |
| Georgian era | 444 | dynasty |
| Stuart period | 327 | dynasty |
| Age of Discovery | 318 | expedition |
| Early Middle Ages | 305 | dynasty |

## Multi-Parent Examples

다중 부모 구조가 적용된 이벤트 예시:

1. **Founding of Mérida**
   - Early modern period (dynasty)
   - Spanish America (dynasty)

2. **Battle of Chillianwala**
   - Modern history (dynasty)
   - Mughal Empire (dynasty)

3. **Lord Roberts's Advance into the Free State**
   - Modern history (dynasty)
   - Scramble for Africa (expedition)

## Period Definitions

### Covered Regions (137 total periods)

| Region | Period Count |
|--------|--------------|
| Europe (Western) | 25 |
| Europe (Eastern) | 8 |
| Middle East | 12 |
| East Asia (China) | 15 |
| East Asia (Japan) | 10 |
| East Asia (Korea) | 8 |
| **India** | 11 |
| **Southeast Asia** | 10 |
| **Africa** | 14 |
| **Americas** | 15 |
| **Russia** | 7 |
| **Central Asia** | 9 |

> *Bold = 새로 추가된 지역*

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Event (wikidata_id?)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Wikidata P361 (Part of)                             │
│ - Confidence: 0.95                                          │
│ - Source: wikidata                                          │
│ - FREE                                                      │
└─────────────────────────────────────────────────────────────┘
                              │ (no result)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Period Matching                                     │
│ - Based on date_start + location                            │
│ - Confidence: 0.70                                          │
│ - Source: period                                            │
│ - FREE                                                      │
└─────────────────────────────────────────────────────────────┘
                              │ (no result)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: LLM Classification                                  │
│ - Uses GPT-4o-mini                                          │
│ - Confidence: varies (0.5-0.9)                              │
│ - Source: llm                                               │
│ - PAID (~$0.01/event)                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    event_parents Table                       │
│ - Multiple parents supported                                │
│ - is_primary flag for main parent                           │
│ - context field for relationship type                       │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /events/hierarchy` | 계층적 트리 구조 반환 |
| `GET /events/aggregates` | Aggregate 이벤트 목록 |
| `GET /events/by-zoom` | 줌 레벨별 이벤트 |
| `GET /events/{id}/children` | 자식 이벤트 목록 |

## Frontend Component

`EventHierarchyPanel` - 트리뷰 컴포넌트

Features:
- Expandable/collapsible tree nodes
- Filter by aggregate type
- Level badges with colors (L0-L4)
- Date range display
- Child count indicators

## Remaining Work

### LLM Classification Required

- **31,672 events** still in `unknown` status
- Estimated cost: ~$320 (at $0.01/event)
- Expected improvement: +50-70% classification rate

### Edge Cases

- 59 Wikipedia URLs with encoding issues
- 190 WorldHistory.org URLs (no Wikidata available)

## Files

### Backend
- `backend/app/models/event.py` - Event model with hierarchy fields
- `backend/app/models/event_parent.py` - Multi-parent relationship
- `backend/app/services/event_service.py` - Hierarchy API logic
- `backend/app/api/v1/events.py` - Hierarchy endpoints

### Pipeline Scripts
- `poc/scripts/hierarchy/unified_classifier.py` - Main classifier
- `poc/scripts/hierarchy/periods.py` - Period definitions
- `poc/scripts/hierarchy/wikidata_client.py` - Wikidata API
- `poc/scripts/hierarchy/llm_classifier.py` - LLM integration
- `poc/scripts/extract_wikidata_ids.py` - Wikipedia→Wikidata extraction

### Frontend
- `frontend/src/components/hierarchy/EventHierarchyPanel.tsx`
- `frontend/src/components/hierarchy/EventHierarchyPanel.css`

---

*Last updated: 2026-01-28*
