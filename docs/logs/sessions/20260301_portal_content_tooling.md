# Portal Content Tooling — 아티클 생성/작성 파이프라인

**날짜**: 2026-03-01

## 목적
트리스메기스토스 포탈에 다큐멘터리 스타일 교양 아티클을 추가하기 위한 도구 구축.
GPT 자동생성 + 사람 수동작성 모두 지원하는 YAML 기반 워크플로우.

## 생성 파일

### 1. `docs/reference/PORTAL_CONTENT.md`
- 콘텐츠 가이드라인 (톤, 구조, 원칙)
- 5개 테마 컬렉션 로드맵 (전쟁의 기술, 신화에서 역사로, 왕과 제국, 사상의 탄생, 모험가와 탐험)
- 각 컬렉션 5개 아티클 = 총 25개 계획
- 섹션 구조: Hook → 배경 → 인물 → 전개 → 전환점 → 결과 → FGO연결(선택)

### 2. `backend/scripts/templates/article_template.yaml`
- 사람이 직접 채울 수 있는 YAML 템플릿
- 모든 필드에 한국어 주석
- 한국어 우선 작성 (ko), en/ja는 비우면 자동번역

### 3. `backend/scripts/create_portal_article.py`
- `--generate "주제"` → GPT-5.2로 YAML 초안 생성 → output/
- `--import file.yaml` → DB에 삽입 (upsert)
- `--import file.yaml --translate` → 빈 en/ja 필드 자동번역 (GPT-5.1)
- `--list` → 현재 portal_items 목록
- `--dry-run` → 미리보기
- 컬렉션 연결 자동 처리

### 4. `backend/scripts/output/` (디렉토리)
- 생성된 YAML 저장소

## 워크플로우

```
자동: --generate "주제" → YAML 검수 → --import
수동: template 복사 → 편집 → --import
번역: --import --translate (빈 en/ja 자동 채움)
```

## 검증
- `--list` ✅ (34개 기존 아이템 확인)
- `--import --dry-run` ✅ (빈 slug 에러 정상 처리)

## 다음 작업
- 첫 번째 아티클 생성 테스트
- 테마 컬렉션 (warfare-tactics 등) DB에 생성
- 기존 서번트 컬럼 섹션 보강 (현재 2~3개 → 5~8개)
