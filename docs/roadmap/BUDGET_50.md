# $50 예산 런치 콘텐츠 계획

## 핵심 판단

**비용의 80%는 GPT 출력 토큰**이다. 모델 선택이 비용을 결정한다.

| 모델 | 입력 | 출력 | 페이지당 비용 |
|------|------|------|-------------|
| gpt-5.2-chat-latest | $1.75/1M | $14.00/1M | **$0.01615** |
| gpt-5.1-chat-latest | $1.25/1M | $10.00/1M | **$0.0115** |

5.1은 5.2 대비 **29% 저렴**. 위젯 생성은 프롬프트가 잘 구조화되어 있어서 5.1로도 품질 충분.

---

## 권장안: gpt-5.1 enhance + 포탈 (총 $49.06)

### A. imp5 시프트 전체 enhance — $41.26

```
모델: gpt-5.1-chat-latest
대상: imp5 시프트 171개, 3,588 페이지 전체
생성물: page_narrative_ko + widgets + camera_altitude (페이지당)
비용: 3,588 × $0.0115 = $41.26
```

이게 가장 효율적인 이유:
- imp5 = 유저가 가장 먼저 보는 시프트 (Reconquista, Cold War, Normandy 등)
- enhance 한 번에 위젯 + 한국어 번역 + 카메라 + 논문 컨텍스트 전부 생성
- **02 위젯 + 03 번역 태스크를 동시에 해결**

### B. 포탈 아이클 22개 — $7.74

```
모델: outline gpt-5.1 / sections gpt-5.1 / translate gpt-5.1
대상: history 20개 + essay 2개
비용: 22 × $0.352 = $7.74
```

5.2 → 5.1로 전환하면 포탈 아이클도 절약:

| 항목 | gpt-5.2 | gpt-5.1 | 절약 |
|------|---------|---------|------|
| 아이클 1개 | $0.352 | $0.252 | 28% |
| 22개 | $7.74 | $5.54 | $2.20 |

**5.1로 전환 시**: 22개 $5.54 → 여유분으로 포탈 30개 가능 ($7.56)

### 총 비용

| 구성 | 비용 | 비고 |
|------|------|------|
| imp5 enhance (5.1) | $41.26 | 171 시프트, 3,588 페이지 |
| 포탈 22개 (5.2) | $7.74 | 또는 5.1으로 30개 ($7.56) |
| **합계** | **$49.00** | 예산 내 |

---

## 대안: imp5 부분 + 포탈 더 많이

포탈 콘텐츠를 더 원하면:

| imp5 시프트 | 페이지 | enhance 비용 | 포탈 수 | 포탈 비용 | 합계 |
|------------|--------|-------------|--------|----------|------|
| 171개 (전체) | 3,588 | $41.26 | 22개 | $7.74 | **$49.00** |
| 123개 | 3,478 | $40.00 | 25개 | $8.80 | **$48.80** |
| 51개 | 3,032 | $34.87 | 40개 | $14.08 | **$48.95** |
| 27개 | 2,582 | $29.69 | 50개 | $17.60 | **$47.29** |

---

## 실행 방법

### Step 1: enhance 배치 스크립트

```bash
cd backend

# imp5 시프트 목록 확인
python scripts/create_shift.py --batch-discover --min-importance 5

# 개별 테스트 (1개 먼저)
python scripts/create_shift.py --enhance 2524 --force  # Battle of Stalingrad

# 배치 실행 (스크립트 필요)
# --model 옵션이 enhance에는 아직 없음 → 코드에서 content_model 변경 필요
```

**필요한 코드 변경**: `create_shift.py`의 `cmd_enhance()`에서 `content_model`을 인자로 받도록 수정.

```python
# 현재 (하드코딩)
content_model = "gpt-5.2-chat-latest"

# 변경
content_model = args.model or "gpt-5.1-chat-latest"  # 기본값을 5.1로
```

### Step 2: 포탈 배치 생성

```bash
# 토픽 목록은 05_PORTAL_CONTENT.md 참조
python scripts/create_portal_article.py --generate "마라톤 전투" --type history --model gpt-5.1-chat-latest
# → YAML 검토 후 import
```

### Step 3: 검증

```bash
# enhance 후
curl http://localhost:8100/api/v1/shifts/2524 | python -m json.tool | head -50

# 포탈 후
python scripts/create_portal_article.py --list
```

---

## 예산 외 무료 작업 (이미 완료/진행 중)

| 태스크 | 상태 | 비용 |
|--------|------|------|
| ErrorBoundary | 완료 | $0 |
| 이벤트 계층 (Wikidata P361) | 스캔 중 | $0 |
| 온보딩 + 투어 진입점 | 완료 | $0 |
| 로드맵 문서 7개 | 완료 | $0 |
