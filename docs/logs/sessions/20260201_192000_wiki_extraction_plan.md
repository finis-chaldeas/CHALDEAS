# 세션: Wikipedia 추출 시스템 설계 및 테스트

**시작**: 2026-02-01 19:20
**목표**: 로컬 Wikipedia ZIM에서 근거 있는 연결만 추출하는 시스템

---

## Phase 1: 로컬 ZIM 구조 파악

### 할 일
1. ZIM 파일에서 읽을 수 있는 데이터 확인
2. 틀(template), 인포박스, 본문, 각주 접근 가능한지 확인
3. 샘플 페이지 하나 완전 분석

### 예상 결과
- ZIM 구조 이해
- 추출 가능한 데이터 목록

---

## Phase 2: 추출 로직 설계

### 추출할 데이터
1. 인포박스: 출생/사망 날짜, 장소, 가족관계
2. 틀(Navbox): 이벤트-인물 그룹핑
3. 본문 링크: 인물/이벤트/장소 연결
4. 각주: 외부 출처

### 소스 구조
```python
{
    "connection": {"from": X, "to": Y, "type": "person_event"},
    "role": "commander",
    "source": {
        "type": "wikipedia_template",
        "article": "Battle of Waterloo",
        "template_name": "Napoleonic Wars",
        "url": "..."
    },
    "evidence_text": "실제 텍스트",
    "references": []  # Wikipedia가 인용한 출처
}
```

---

## Phase 3: 소규모 테스트

### 테스트 대상
- 1개 이벤트 페이지 (Battle of Waterloo)
- 1개 인물 페이지 (Napoleon)

### 검증 항목
- 틀 파싱 되는지
- 인포박스 파싱 되는지
- 링크 추출 되는지
- 각주 접근 되는지

---

## Phase 4: 결과 문서화

### 문서화 내용
- 성공한 것
- 실패한 것
- 개선 방안

---

## 작업 시작
