# Shift Card (히스토리 시프트 프리뷰)

## 와이어프레임

```
┌─────────────────────────┐
│ Greco-Persian Wars      │
│ 그리스-페르시아 전쟁      │
│                         │
│ 499 — 449 BCE           │
│ 15 pages                │
│ ★★★★★                  │
│                         │
│ "기원전 499년, 이오니아   │  ← chain_segments.page_narrative (1페이지)
│  도시들의 반란이..."      │     처음 150자
│                         │
│ [▶ 재생하기]             │
└─────────────────────────┘
```

## 데이터 소스

| 필드 | 테이블.컬럼 | 비고 |
|------|------------|------|
| 제목 | `historical_chains.title` / `title_ko` | |
| 기간 | `historical_chains.year_start`, `year_end` | |
| 페이지 수 | `chain_segments` COUNT | |
| 중요도 | `historical_chains.importance` | |
| 본문 스니펫 | `chain_segments.page_narrative` | **1페이지(seq=0)의 처음 150자** |

## 본문 소스

chain_segments.page_narrative가 이미 페이지별 서사 텍스트.
→ 첫 페이지 텍스트를 잘라서 프리뷰로 사용. 추가 텍스트 생성 불필요.

## 트리거

- ShiftBrowser 목록에서 시프트 클릭
- `[Name](entity:shift:id)` 엔티티 링크 클릭
- Event/Person Card의 "시프트" 버튼

## 액션 버튼

- **▶ 재생하기** → ShiftPanel 시작 (현재와 동일)

## 기존 코드 참고

- ShiftBrowser: `frontend/src/components/shift/ShiftBrowser.tsx`
- ShiftPanel: `frontend/src/components/shift/ShiftPanel.tsx`
- chain 모델: `backend/app/models/v1/chain.py`
- shifts API: `backend/app/api/v1/shifts.py`
