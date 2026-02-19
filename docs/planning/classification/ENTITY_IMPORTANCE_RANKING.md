# 엔티티 중요도 랭킹 시스템 설계

## 문제 정의

CHALDEAS 데이터 규모:
- **현재**: Wikidata 기반 52만 인물, 5.6만 이벤트, 4만 장소
- **예정**: Gutenberg + 기타 책들에서 **수백만 엔티티** 추가

이 중 대부분은 Wikidata에 없음. 따라서:
- ❌ Wikidata 의존 불가
- ✅ **자체 데이터 기반** 중요도 산정 필수

**필요한 것**: 외부 의존 없이 자동으로 중요도를 판별하여 UI/검색/추천에 활용

---

## 접근법 비교

### 접근법 1: Wikidata Sitelinks 수

**방식**: Wikipedia 문서가 몇 개 언어로 존재하는지

| 인물 | Sitelinks | 의미 |
|------|-----------|------|
| 나폴레옹 | 283 | 283개 언어 Wikipedia에 문서 |
| 베토벤 | 269 | 세계적 인물 |
| 무명 화가 | 3 | 소수 언어만 |

**장점**:
- 객관적 지표 (Wikipedia 커뮤니티가 결정)
- 글로벌 인지도 반영
- 한 번 가져오면 됨

**단점**:
- Wikidata 의존
- 최근 인물은 과소평가될 수 있음
- 스냅샷 (시간 지나면 outdated)

**평가**: ⭐⭐⭐⭐⭐ 가장 신뢰할 수 있는 초기 시드

---

### 접근법 2: Wikipedia PageRank

**방식**: Wikipedia 내부 링크 그래프에서 PageRank 계산

**장점**:
- 학술적으로 검증된 방법
- 링크 구조 기반 중요도

**단점**:
- 전체 Wikipedia 그래프 필요 (매우 큼)
- 계산 복잡
- 우리가 직접 계산하기 어려움

**평가**: ⭐⭐⭐ 좋지만 구현 비용 높음

---

### 접근법 3: 자체 데이터 기반 (mentions, links, sources)

**방식**: 우리가 추출한 데이터에서 계산

```
importance = mentions_count × 0.3
           + links_count × 0.3
           + sources_count × 0.2
           + aliases_count × 0.2
```

**장점**:
- 외부 의존 없음
- 데이터 쌓일수록 정확해짐
- 실시간 업데이트 가능

**단점**:
- Cold Start 문제 (아직 추출 안 된 엔티티는 0점)
- 추출 편향 반영 (우리가 뭘 추출했느냐에 따라 달라짐)
- 현재는 데이터 부족

**평가**: ⭐⭐⭐⭐ 장기적으로 좋지만 초기에는 부족

---

### 접근법 4: 외부 데이터셋 (Pantheon, etc.)

**방식**: MIT Pantheon 같은 역사적 인물 랭킹 데이터 사용

**장점**:
- 전문가가 큐레이션
- 학술적 검증

**단점**:
- 인물만 커버 (이벤트, 장소 없음)
- 제한된 수 (~10만명)
- 외부 의존

**평가**: ⭐⭐⭐ 보조 자료로는 좋음

---

### 접근법 5: 하이브리드 (권장)

**방식**:
1. 초기: Wikidata sitelinks로 시드
2. 운영: 자체 데이터로 보완/재계산
3. 장기: 자체 데이터 비중 점진적 증가

---

## 권장 접근법: 자체 데이터 기반 (Primary)

### 핵심 원칙

```
┌─────────────────────────────────────────────────────────────┐
│  Primary: 자체 데이터 기반 점수                             │
│           mentions × sources × links                        │
│                                                             │
│  Bonus: Wikidata sitelinks (있으면 가산점)                  │
└─────────────────────────────────────────────────────────────┘
```

**이유**: Gutenberg 등에서 수백만 엔티티가 추가될 예정이며, 대부분 Wikidata에 없음

### 점수 계산 공식

```python
import math

def calculate_importance(entity):
    """
    자체 데이터 기반 중요도 계산

    - mentions_count: 전체 텍스트에서 언급된 횟수
    - sources_count: 몇 개의 독립된 출처(책, 문서)에서 언급되었나
    - links_count: 다른 엔티티와의 연결 수
    - aliases_count: 별칭 수 (다양한 이름 = 유명)
    - sitelinks_count: Wikidata sitelinks (있으면 보너스)
    """

    # 로그 스케일로 정규화 (큰 값 차이 완화)
    m = math.log(entity.mentions_count + 1)
    s = math.log(entity.sources_count + 1)
    l = math.log(entity.links_count + 1)
    a = math.log(entity.aliases_count + 1)

    # 가중 합산
    score = (
        m * 0.35 +    # 언급 빈도 (가장 중요)
        s * 0.30 +    # 출처 다양성 (여러 책에 나오면 중요)
        l * 0.25 +    # 관계 수 (네트워크 중심성)
        a * 0.10      # 별칭 다양성
    )

    # Wikidata 있으면 보너스 (최대 10% 가산)
    if entity.sitelinks_count > 0:
        bonus = min(math.log(entity.sitelinks_count) * 0.05, 0.5)
        score += bonus

    return score

def calculate_tier(score):
    """점수 기반 티어 결정"""
    if score >= 8.0: return 'S'   # 세계사적 인물
    if score >= 6.0: return 'A'   # 매우 유명
    if score >= 4.0: return 'B'   # 유명
    if score >= 2.0: return 'C'   # 알려진
    return 'D'                     # 마이너
```

### 예시 시나리오

| 인물 | Wikidata | mentions | sources | links | 점수 | 티어 |
|------|----------|----------|---------|-------|------|------|
| 나폴레옹 | ✅ 283 | 50,000 | 500 | 3,000 | ~10 | S |
| 셰익스피어 | ✅ 270 | 30,000 | 400 | 2,000 | ~9.5 | S |
| 책 속 주인공 | ❌ | 10,000 | 1 | 50 | ~4.5 | B |
| 여러 책의 인물 | ❌ | 500 | 50 | 100 | ~5.5 | A |
| 한 번 언급된 인물 | ❌ | 1 | 1 | 0 | ~0.5 | D |

**핵심 인사이트**:
- 한 책에서 10,000번 언급 < 50개 책에서 500번 언급
- **sources_count가 중요** (다양한 출처 = 범용적 중요성)

### 테이블 구조

```sql
-- 별도 테이블로 관리 (엔티티 테이블 오염 방지)
CREATE TABLE entity_importance (
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,

    ---------------------------------------------------------------
    -- 원본 지표 (Raw Metrics) - 항상 보존, 로직 변경 시 재계산용
    ---------------------------------------------------------------
    mentions_count INTEGER DEFAULT 0,      -- 전체 언급 횟수
    sources_count INTEGER DEFAULT 0,       -- 언급된 출처(책/문서) 수
    links_count INTEGER DEFAULT 0,         -- 연결된 엔티티 수
    aliases_count INTEGER DEFAULT 0,       -- 별칭 수
    sitelinks_count INTEGER,               -- Wikidata sitelinks (nullable)

    -- 추가 원본 지표 (향후 확장)
    incoming_links INTEGER DEFAULT 0,      -- 들어오는 링크 수
    outgoing_links INTEGER DEFAULT 0,      -- 나가는 링크 수
    distinct_languages INTEGER DEFAULT 0,  -- 몇 개 언어로 별칭 있나

    ---------------------------------------------------------------
    -- 계산 결과 (Computed) - 로직 변경 시 재계산
    ---------------------------------------------------------------
    importance_score FLOAT DEFAULT 0,
    importance_tier CHAR(1) DEFAULT 'D',
    scoring_version VARCHAR(10) DEFAULT 'v1',  -- 어떤 로직으로 계산했나

    ---------------------------------------------------------------
    -- 메타
    ---------------------------------------------------------------
    raw_updated_at TIMESTAMP,              -- 원본 지표 마지막 업데이트
    score_updated_at TIMESTAMP,            -- 점수 마지막 계산
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (entity_type, entity_id)
);

-- 인덱스
CREATE INDEX idx_importance_tier ON entity_importance(importance_tier);
CREATE INDEX idx_importance_score ON entity_importance(importance_score DESC);
CREATE INDEX idx_importance_version ON entity_importance(scoring_version);
```

### 로직 버전 관리

```python
# 점수 계산 로직 버전별 정의
SCORING_VERSIONS = {
    'v1': {
        'weights': {
            'mentions': 0.35,
            'sources': 0.30,
            'links': 0.25,
            'aliases': 0.10,
        },
        'sitelinks_bonus': 0.05,
        'description': '초기 버전 - mentions 중심'
    },
    'v2': {
        'weights': {
            'mentions': 0.20,
            'sources': 0.50,  # sources 비중 증가
            'links': 0.20,
            'aliases': 0.10,
        },
        'sitelinks_bonus': 0.05,
        'description': 'sources 중심 - 다양한 출처 우대'
    },
}

def calculate_score(entity, version='v1'):
    """버전별 점수 계산"""
    config = SCORING_VERSIONS[version]
    w = config['weights']

    score = (
        math.log(entity.mentions_count + 1) * w['mentions'] +
        math.log(entity.sources_count + 1) * w['sources'] +
        math.log(entity.links_count + 1) * w['links'] +
        math.log(entity.aliases_count + 1) * w['aliases']
    )

    if entity.sitelinks_count:
        score += math.log(entity.sitelinks_count) * config['sitelinks_bonus']

    return score, version

def recalculate_with_new_version(new_version):
    """
    새 로직으로 전체 재계산
    원본 지표(raw metrics)는 그대로, 점수만 재계산
    """
    cursor.execute("""
        SELECT entity_type, entity_id,
               mentions_count, sources_count, links_count,
               aliases_count, sitelinks_count
        FROM entity_importance
    """)

    for row in cursor.fetchall():
        score, version = calculate_score(row, new_version)
        tier = calculate_tier(score)

        cursor.execute("""
            UPDATE entity_importance
            SET importance_score = %s,
                importance_tier = %s,
                scoring_version = %s,
                score_updated_at = NOW()
            WHERE entity_type = %s AND entity_id = %s
        """, (score, tier, version, row.entity_type, row.entity_id))
```

### 로직 변경 시 워크플로우

```
1. 새 버전 정의 (SCORING_VERSIONS에 'v3' 추가)
2. recalculate_with_new_version('v3') 실행
3. 결과 검토 (상위 100개 비교 등)
4. 문제 없으면 프로덕션 적용
5. 문제 있으면 이전 버전으로 롤백 (재계산)
```

### 재계산 배치

```python
def recalculate_all_importance():
    """
    주기적으로 실행 (매일 또는 매주)
    새 책 추가 후 실행
    """

    for entity_type in ['person', 'event', 'location']:
        # 1. mentions 집계
        cursor.execute(f"""
            UPDATE entity_importance ei
            SET mentions_count = (
                SELECT COUNT(*) FROM mentions m
                JOIN links l ON m.link_id = l.id
                WHERE l.to_type = %s AND l.to_id = ei.entity_id
            )
            WHERE ei.entity_type = %s
        """, (entity_type, entity_type))

        # 2. sources 집계
        cursor.execute(f"""
            UPDATE entity_importance ei
            SET sources_count = (
                SELECT COUNT(DISTINCT s.id) FROM sources s
                JOIN mentions m ON m.source_id = s.id
                JOIN links l ON m.link_id = l.id
                WHERE l.to_type = %s AND l.to_id = ei.entity_id
            )
            WHERE ei.entity_type = %s
        """, (entity_type, entity_type))

        # 3. links 집계
        # 4. 점수 계산
        # 5. 티어 결정
```

---

## Wikidata Sitelinks (보조)

Wikidata가 있는 엔티티에 대해서만 sitelinks를 가져와 보너스로 사용.

```python
# 선택적: Wikidata 엔티티에 대해 sitelinks 수집
def fetch_sitelinks_for_wikidata_entities():
    """
    wikidata_id가 있는 엔티티만 대상
    한 번 수집 후 저장
    """
    pass
```

---

## 결론

### 구현 순서

| 단계 | 작업 | 우선순위 |
|------|------|----------|
| 1 | `entity_importance` 테이블 생성 | 높음 |
| 2 | 현재 데이터로 초기 점수 계산 | 높음 |
| 3 | Wikidata sitelinks 수집 (보너스) | 중간 |
| 4 | 재계산 배치 스크립트 | 중간 |
| 5 | API/UI 연동 | 낮음 |

### 핵심 포인트

1. **자체 데이터가 Primary** - Wikidata 의존 X
2. **sources_count 중시** - 여러 책에 나오면 중요
3. **로그 스케일** - 극단값 완화
4. **별도 테이블** - 엔티티 테이블 오염 방지
5. **주기적 재계산** - 새 책 추가 시 업데이트

---

## 활용처

- **검색 결과 정렬**: S티어 먼저 표시
- **자동완성**: 유명 인물 우선
- **그래프 시각화**: 중요 노드 크게 표시
- **추천**: "관련 주요 인물" 필터링
- **데이터 품질**: D티어는 검증 우선순위 낮춤
- **Cold Start 해결**: 새 엔티티도 mentions/sources 기반으로 즉시 랭킹

---

## 타임라인

```
현재: Wikipedia 추출 완료 후 → 초기 점수 계산
      (mentions, sources, links 데이터 있음)

이후: Gutenberg 책 추가 → 재계산
      (새 엔티티도 자동으로 랭킹)

장기: 모든 책 추가 완료 → 안정적 티어 시스템
      (Wikidata 없어도 완전 독립 운영)
```
