# 세션 로그: 2026-02-01 20:30

## 세션 정보
- **플랜 체크포인트**: CP-3.3 (인물-이벤트 연결 강화)
- **목적**: Wikipedia 추출 파이프라인 완성

## 작업 목록
1. [x] DB 매칭 스크립트 작성
2. [x] 대규모 추출 (90개 이벤트)
3. [x] 연결 유형 분류 (58,079개 타이틀)
4. [x] 새 테이블에 저장 (wiki_connections)

---

## 1. DB 매칭 스크립트 (완료)

**파일**: `poc/scripts/v2/match_wiki_to_db.py`

---

## 2. 대규모 추출 (완료)

**입력**: `poc/data/wikipedia_extract/event_list_100.txt`

**결과**:
- Events processed: 90
- Body connections: 141,875
- Navbox connections: 61,925
- **Total: 203,800 connections**

**생성된 파일**:
- `poc/data/wikipedia_extract/extract_20260201_200938.json`

---

## 3. 연결 유형 분류 (완료)

**58,079개 unique 타이틀 분류**:
- With QID: 23,558 (41%)
  - Person: 6,566
  - Event: 1,840
  - Location: 125
  - Not in DB: 15,027
- Without QID: 34,521

**생성된 파일**:
- `poc/data/wikipedia_extract/classified_20260201_202112.json`

---

## 4. DB 저장 (완료)

**새 테이블 생성**: `wiki_connections`

```sql
CREATE TABLE wiki_connections (
    id SERIAL PRIMARY KEY,
    from_event_id INTEGER REFERENCES events(id),
    from_event_qid VARCHAR(20),
    from_event_title VARCHAR(500),
    to_entity_id INTEGER,
    to_entity_type VARCHAR(20),  -- person, event, location
    to_entity_qid VARCHAR(20),
    to_entity_title VARCHAR(500),
    connection_type VARCHAR(50),  -- body, navbox
    navbox_group VARCHAR(200),
    evidence_text TEXT,
    source_url VARCHAR(500),
    created_at TIMESTAMP,
    confidence FLOAT
);
```

**저장 결과**:
- **Total: 28,666 connections with evidence**
- Person (body): 11,637
- Person (navbox): 3,063
- Event (body): 8,831
- Event (navbox): 4,774
- Location (body): 315
- Location (navbox): 46

---

## 생성된 파일

| 파일 | 설명 |
|------|------|
| `poc/scripts/v2/extract_wiki_connections.py` | Wikipedia 추출 스크립트 |
| `poc/scripts/v2/match_wiki_to_db.py` | DB 매칭 스크립트 |
| `poc/scripts/v2/classify_connections.py` | 연결 분류 스크립트 |
| `poc/scripts/v2/save_to_wiki_connections.py` | 새 테이블 저장 스크립트 |
| `poc/data/wikipedia_extract/event_list_100.txt` | 이벤트 목록 |
| `poc/data/wikipedia_extract/extract_*.json` | 추출 결과 |
| `poc/data/wikipedia_extract/classified_*.json` | 분류 결과 |

---

## 결과

**성공**:
- Wikipedia에서 근거 있는 연결 28,666개 추출 및 저장
- 모든 연결에 evidence_text 또는 navbox_group 포함
- source_url로 출처 추적 가능

**핵심 성과**:
- 기존 연결: 318,370개 (근거 0개)
- 새 연결: 28,666개 (근거 100%)

---

## 다음 작업

1. 더 많은 이벤트 추출 (현재 90개 → 1000개+)
2. QID 없는 34,521개 타이틀 처리 방안
3. 백엔드 API에서 wiki_connections 활용
