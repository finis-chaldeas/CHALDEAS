# Phase 3: API 변경

## 목표

카드에 필요한 데이터를 효율적으로 제공.

## 현재 API 커버리지

| 카드 | API | 상태 |
|------|-----|------|
| Event | smart-markers (description[:200] 포함) | ✅ 이미 있음 |
| Person | `GET /api/v1/persons/{id}` | ✅ 있음 |
| Location | `GET /api/v1/locations/{id}` | ✅ 있음 |
| Servant | `GET /api/v1/servants/by-person/{personId}` | ✅ 있음 |
| Shift | `GET /api/v1/shifts/{id}` | ✅ 있음 |
| Resolve | `GET /api/v1/portal/resolve` | ✅ 있음 |

## 추가 작업

### 1. Person API에 FGO 서번트 포함 (선택)

**옵션 A**: Person 응답에 `fgo_servant` 필드 추가
```json
{
  "id": 123,
  "name": "Alexander the Great",
  "details": { "biography": "..." },
  "fgo_servant": {              // ← 추가
    "name": "Iskandar",
    "class_name": "Rider",
    "rarity": 5,
    "portrait_url": "..."
  }
}
```

**옵션 B**: 프론트에서 병렬 fetch
```typescript
const [person, servant] = await Promise.all([
  personsApi.get(id),
  servantsApi.getByPerson(id)  // 이미 존재
])
```

**추천: 옵션 B** — 기존 API 안 건드리고, 프론트에서 병렬로 가져오면 충분.

### 2. Shift 프리뷰 데이터

현재 shifts API가 page_narrative를 반환하는지 확인 필요.
→ 안 하면: 첫 segment의 page_narrative[:150]을 shifts 응답에 추가.

### 3. Location의 주요 이벤트

`GET /api/v1/locations/{id}` 응답에 이벤트 목록이 포함되는지 확인.
→ 안 되면: `event_locations` JOIN으로 importance 상위 3개 추가.

## 선행 조건

- Phase 0-1 진행 중 API 필요 사항이 구체화되면 작업

## 예상 영향

- 기존 API 수정 최소화 (병렬 fetch 방식 채택 시)
- 필요 시 shifts, locations API에 필드 추가
