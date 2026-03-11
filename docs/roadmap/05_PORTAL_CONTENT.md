# 05. 포탈 콘텐츠 배치 생성

## 문제

포탈(TRISMEGISTOS)에 아이템이 34개뿐이고, 그 중 history 타입은 3개. "읽을 게 없다" 느낌.
최소 100개는 있어야 컬렉션 브라우징이 의미가 있다.

## 현재 상태

| 타입 | 수 |
|------|-----|
| servant_column | 12 |
| singularity | 8 |
| lostbelt | 7 |
| history | 3 |
| music | 2 |
| literature | 2 |
| **합계** | **34** |

- 한국어 제목/설명: 100% 커버
- sources 필드: 일부만
- 논문 통합: 구현 완료 (`create_portal_article.py`에 반영됨)

## 실행 계획

### 1단계: history 아티클 50개 생성

주요 역사 토픽을 선정하여 배치 생성:

```bash
cd backend

# 개별 생성 (테스트)
python scripts/create_portal_article.py --generate "마라톤 전투" --type history
python scripts/create_portal_article.py --generate "십자군 전쟁" --type history --theme warfare
python scripts/create_portal_article.py --generate "실크로드" --type history --theme trade

# 생성 → 검토 → import
python scripts/create_portal_article.py --import scripts/output/marathon-battle.yaml --translate
```

**토픽 후보 (50개)**:

고대:
- 마라톤 전투, 테르모필레, 살라미스 해전
- 알렉산더 대왕의 동방원정
- 포에니 전쟁, 한니발의 알프스 횡단
- 카이사르와 루비콘 강
- 클레오파트라와 이집트의 몰락
- 로마 제국의 흥망
- 진시황과 만리장성
- 페르시아 제국

중세:
- 십자군 전쟁
- 몽골 제국의 세계정복
- 비잔틴 제국의 천년
- 바이킹 시대
- 백년전쟁과 잔 다르크
- 레콘키스타
- 오스만 제국의 부상

근세:
- 대항해시대
- 르네상스
- 종교개혁
- 30년 전쟁
- 명나라의 멸망
- 무굴 제국

근대:
- 프랑스 혁명
- 나폴레옹 전쟁
- 산업혁명
- 미국 독립전쟁
- 메이지 유신
- 아편전쟁

현대:
- 1차 세계대전
- 2차 세계대전
- 냉전
- 한국전쟁
- 베트남 전쟁

### 2단계: essay 타입 20개

역사 에세이/분석:
- "팔랑크스에서 총기까지 — 전쟁의 진화"
- "향신료 무역이 세계를 바꾸다"
- "전염병이 역사를 움직인 순간들"
- "왕조의 몰락 패턴"
- 등

### 3단계: 컬렉션 구성

생성된 아이템들을 테마별 컬렉션으로 묶기:
- "Ancient Warfare" (고대 전쟁)
- "Empires Rise and Fall" (제국의 흥망)
- "Turning Points" (역사의 전환점)
- "East Meets West" (동서 교류)

## 배치 스크립트 (필요시)

```python
# scripts/batch_generate_articles.py
TOPICS = [
    ("마라톤 전투", "history", "warfare"),
    ("십자군 전쟁", "history", "warfare"),
    # ...
]

for topic, item_type, theme in TOPICS:
    # generate → YAML
    # 수동 검토 후 import
```

생성만 자동, import는 검토 후 수동 권장 (품질 관리).

## 비용 추정

| 단계 | 아이템 수 | 섹션/아이템 | 비용 |
|------|----------|-----------|------|
| outline (gpt-5.2) | 70 | 1 | ~$2 |
| sections (gpt-5.2-chat) | 70 | 6~8 | ~$35 |
| translation (gpt-5.1) | 70 | 8~10 fields | ~$20 |
| **합계** | | | **~$57** |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/scripts/batch_generate_articles.py` | **신규** (선택) — 토픽 목록 + 배치 루프 |

기존 `create_portal_article.py`는 이미 완성. 배치 래퍼만 필요.

## 검증

```bash
# 생성 확인
python scripts/create_portal_article.py --list

# 프론트 확인
# TRISMEGISTOS 포탈 → 컬렉션 브라우징 → 아이템 상세
```
