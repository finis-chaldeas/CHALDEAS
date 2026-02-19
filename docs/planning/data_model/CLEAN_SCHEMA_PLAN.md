# CHALDEAS 클린 스키마 기획서

## 1. 목적

**"모든 역사는 누가(Person) 어디서(Location) 언제(Time) 무엇을(Event) 했는가"**

3D 지구본에서 BCE 3000 ~ 현재까지의 역사를 탐색.
모든 연결에는 **근거(evidence)**가 있어야 함.

---

## 2. 핵심 테이블 (4개)

### 2.1 persons (누가)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| name | VARCHAR | 이름 |
| name_ko | VARCHAR | 한국어 이름 |
| wikidata_id | VARCHAR | Wikidata QID |
| birth_year | INTEGER | 출생 연도 (음수 = BCE) |
| death_year | INTEGER | 사망 연도 |
| description | TEXT | 설명 |

### 2.2 locations (어디서)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| name | VARCHAR | 이름 |
| name_ko | VARCHAR | 한국어 이름 |
| wikidata_id | VARCHAR | Wikidata QID |
| latitude | FLOAT | 위도 |
| longitude | FLOAT | 경도 |

### 2.3 events (무엇을 + 언제)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| title | VARCHAR | 제목 |
| title_ko | VARCHAR | 한국어 제목 |
| wikidata_id | VARCHAR | Wikidata QID |
| date_start | INTEGER | 시작 연도 (음수 = BCE) |
| date_end | INTEGER | 종료 연도 |
| description | TEXT | 설명 |

### 2.4 connections (연결 - 근거 필수)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER | PK |
| from_type | VARCHAR | person, location, event |
| from_id | INTEGER | 연결 주체 ID |
| from_qid | VARCHAR | Wikidata QID |
| to_type | VARCHAR | person, location, event |
| to_id | INTEGER | 연결 대상 ID |
| to_qid | VARCHAR | Wikidata QID |
| relation | VARCHAR | 관계 유형 |
| **evidence** | TEXT | **근거 (필수!)** |
| source_url | VARCHAR | 출처 URL |
| source_type | VARCHAR | wikipedia, wikidata, book |
| confidence | FLOAT | 신뢰도 |

---

## 3. 관계 유형 (relation)

### Person-Event
- `participant` - 참여자
- `leader` - 지도자
- `commander` - 지휘관
- `victim` - 피해자
- `founder` - 창시자

### Event-Location
- `occurred_at` - 발생 장소
- `origin` - 출발지
- `destination` - 목적지

### Event-Event
- `part_of` - 상위 이벤트의 일부
- `causes` - 원인
- `follows` - 뒤따름

### Person-Person
- `parent` - 부모
- `teacher` - 스승
- `rival` - 경쟁자

### Person-Location
- `birthplace` - 출생지
- `deathplace` - 사망지
- `ruled` - 통치

---

## 4. 데이터 소스

### 4.1 Wikidata (구조화 데이터)
- P31 (instance of) - 엔티티 유형
- P361 (part of) - 계층 관계
- P710 (participant) - 이벤트 참여자
- P276 (location) - 발생 장소

### 4.2 Wikipedia (근거 텍스트)
- 로컬 ZIM 파일: `data/kiwix/wikipedia_en_nopic.zim`
- 본문에서 context 추출
- Navbox에서 관련 항목 추출

---

## 5. 파이프라인

```
1. Wikidata에서 주요 이벤트 목록 가져오기
   └─ P31 = battle, war, revolution 등

2. 각 이벤트의 Wikipedia 페이지 열기
   └─ ZIM 파일에서 HTML 추출

3. 관련 인물/장소 링크 추출
   └─ 본문 링크 + Navbox

4. 각 링크에서 QID 추출
   └─ Wikipedia → Wikidata 매핑

5. DB의 persons/locations/events와 매칭
   └─ QID로 매칭

6. connections 테이블에 저장
   └─ evidence = 본문 context
   └─ source_url = Wikipedia URL
```

---

## 6. 검증 기준

### 6.1 데이터 품질
- [ ] 모든 connections에 evidence 있음
- [ ] 모든 connections에 source_url 있음
- [ ] evidence가 의미있는 문장임 (잡다한 텍스트 X)

### 6.2 커버리지
- [ ] 주요 전쟁 100개 이상
- [ ] 주요 인물 1000명 이상
- [ ] 이벤트당 평균 5개 이상 연결

### 6.3 정확도
- [ ] QID 매칭 정확도 95% 이상
- [ ] 관계 유형 분류 정확도 80% 이상

---

## 7. 기존 테이블 처리

### 유지
- `persons` - 핵심 테이블
- `locations` - 핵심 테이블
- `events` - 핵심 테이블

### 삭제 대상
- `wiki_connections` - 임시 테이블
- `event_persons` - connections로 대체
- `event_locations` - connections로 대체
- `event_relationships` - connections로 대체
- `person_event_roles` - connections로 대체
- `event_relations_v2` - connections로 대체
- 기타 V0/V1/V2 중복 테이블

### 보류
- `sources` - 책 출처 (나중에 연동)
- `categories` - 분류 (나중에 연동)

---

## 8. 작업 순서

1. [ ] 기획서 확정
2. [ ] connections 테이블 생성
3. [ ] Wikipedia 파이프라인 개선 (evidence 품질)
4. [ ] 주요 이벤트 100개 추출
5. [ ] connections 채우기
6. [ ] 검증
7. [ ] 기존 쓰레기 테이블 삭제
8. [ ] 백엔드 API 연동
9. [ ] 프론트엔드 연동

---

## 9. 예상 결과

| 항목 | 목표 |
|------|------|
| persons | 기존 425,552 중 QID 있는 241,805 유지 |
| locations | 기존 40,613 중 QID 있는 1,609 유지 |
| events | 기존 56,567 중 QID 있는 14,131 유지 |
| connections | 새로 생성, 근거 있는 것만 |
