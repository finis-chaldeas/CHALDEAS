# 세션 로그: 2026-02-01 20:00

## 세션 정보
- **플랜 체크포인트**: CP-3.3 (인물-이벤트 연결 강화) 준비
- **목적**: Wikipedia HTML 구조 분석하여 링크 추출 패턴 수정

## 배경
- 이전 세션에서 `extract_wiki_connections.py` 작성
- 링크 추출 regex가 0개 나오는 문제
- HTML 구조 분석 필요

## 완료된 작업

### 1. 문제 발견 및 수정
- **문제**: 기존 코드가 `href.startswith('./')` 체크
- **실제**: ZIM 파일의 링크는 `./` 없이 바로 `href="Article_Name"` 형식
- **수정**: 링크 추출 조건 변경

### 2. HTML 구조 분석
- Battle of Waterloo HTML 분석 (577,817 chars)
- 링크 형식: `<a href="Napoleon">Napoleon</a>`
- Navbox 구조: `navbox-group` + `navbox-list` 쌍으로 구성
- Infobox: 기본 정보 (date, location, result)
- Wikidata 링크: `wikidata.org/wiki/Q12345` 형식으로 발견

### 3. 스크립트 확장
- `extract_wiki_connections.py` 대폭 수정
- 추가 기능:
  - Navbox 파싱 (관련 전투, 참전국 추출)
  - Infobox 파싱 (날짜, 장소, 결과)
  - source 정보 포함 (wikipedia_body, wikipedia_navbox)
  - **Wikidata QID 추출** (이벤트 자체 + 각 연결 대상)
  - JSON 저장 기능 (--save 옵션)
  - QID 해석 옵션 (--resolve-qids)

### 4. 테스트 결과

**기본 테스트 (5개 이벤트)**:
```
Events processed: 5
Body connections with evidence: 8,924
Navbox connections: 3,454
Total connections: 12,378
```

**QID 해석 테스트 (Battle of Waterloo)**:
```
Event: Battle of Waterloo (QID: Q48314)
Body connections with QID: 555/1092 (51%)
Navbox connections with QID: 148/402 (37%)
```

**핵심 인물 QID 확인**:
- Napoleon I: Q517
- Michel Ney: Q40756
- William Sadler II: Q5015030

**관련 이벤트 QID 확인**:
- Battle of Ligny: Q855429
- Napoleonic Wars: Q78994
- Battle of Quatre Bras: Q705936

## 변경된 파일
- `poc/scripts/v2/extract_wiki_connections.py` - 수정

## 생성된 파일
- `poc/data/wikipedia_extract/extract_20260201_192204.json` - 기본 추출
- `poc/data/wikipedia_extract/extract_20260201_192508.json` - QID 포함

## 결과
- **성공**:
  - 링크 추출 정상 작동
  - 근거(evidence_text) 있는 연결 추출 가능
  - Wikidata QID 자동 추출 가능

## 다음 작업

### 즉시 가능
1. **DB 매칭 스크립트 작성**
   - 추출된 QID를 DB의 persons/events/locations와 매칭
   - 매칭되면 V2 테이블에 연결 생성

2. **연결 저장 스크립트**
   - `event_relations_v2` 또는 새 테이블에 저장
   - evidence_text, source 포함

### 추가 개선
3. **연결 유형 분류**
   - 인물 vs 이벤트 vs 장소 분류
   - Wikidata의 instance_of (P31) 속성 활용

4. **역할 추론**
   - commander, participant, victim 등
   - Navbox 그룹명 활용 (예: "Leaders", "Belli-gerents")

5. **대규모 추출**
   - 주요 이벤트 목록 작성 (전쟁, 왕조, 혁명 등)
   - 배치 처리로 전체 추출

## 기술 노트

### ZIM 파일 구조
- 경로: `A/Article_Title` (공백 → 언더스코어)
- 링크: `href="Article_Name"` (상대 경로, ./ 없음)
- Wikidata: `wikidata.org/wiki/Q12345` 형식

### QID 캐시
- `_qid_cache` 딕셔너리로 중복 조회 방지
- 메모리 내 캐시 (세션 간 유지 안 됨)
