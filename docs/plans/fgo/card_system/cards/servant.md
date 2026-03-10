# Servant Card (FGO 전용)

## 와이어프레임

```
┌─────────────────────────┐
│ [FGO Portrait]          │  ← portrait_url (Atlas Academy)
│                         │
│ ★★★★★ Rider            │
│ Iskandar                │
│ イスカンダル              │
│ 이스칸다르                │
│                         │
│ NP: Ionioi Hetairoi     │
│                         │
│ Historical:             │
│  Alexander the Great    │  ← 클릭 시 Person Card
│                         │
│ [서번트 칼럼]             │
└─────────────────────────┘
```

## 데이터 소스

| 필드 | 테이블.컬럼 | 비고 |
|------|------------|------|
| 이름 | `fgo_servants.name` / `name_jp` / `name_ko` | |
| 클래스 | `fgo_servants.class_name` | Saber, Archer, ... |
| 레어도 | `fgo_servants.rarity` | ★ 1-5 |
| 보구 | `fgo_servants.noble_phantasm` | |
| 초상화 | `fgo_servants.portrait_url` | Atlas Academy |
| 역사 인물 | `fgo_servants.person_id` → `persons` | 매칭 있을 때 |

## 본문 소스

fgo_servants에 description 필드 없음.
→ 초상화 + 메타데이터 중심. 텍스트는 person_details.biography에서 가져옴.

## 트리거

- 포탈 서번트 이름 클릭
- Person Card의 FGO 섹션 클릭 (역방향)

## 액션 버튼

- **서번트 칼럼** → portal_items (item_type='servant_column') 연결
- **역사 인물 보기** → Person Card 열기
- **시프트** → 관련 시프트 (있으면)

## 기존 코드 참고

- FGO 모델: `backend/app/models/v2/fgo.py`
- Servants API: `backend/app/api/v1/servants.py`
- Person 연결: `servantsApi.getByPerson(personId)` (프론트)
