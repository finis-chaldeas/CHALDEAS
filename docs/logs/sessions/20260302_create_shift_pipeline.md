# 20260302 — History Shift 자동생성 파이프라인

## 목적

GPT를 활용한 History Shift 자동 생성 스크립트 구현. `create_portal_article.py`의 2-step agent 패턴을 시프트에 적용.

## 변경 파일

### 신규
- `backend/scripts/create_shift.py` — 메인 스크립트 (생성/임포트/번역/목록)
- `backend/scripts/templates/shift_template.yaml` — 수동 작성용 템플릿

## 구현 내용

### 3-Step Agent 파이프라인
1. **Step 0**: `gather_context()` — DB에서 관련 events/persons/locations 조회
2. **Step 1**: Outline (gpt-5.2 reasoning) → JSON 구조 + 엔티티 ID + 위젯 힌트
3. **Step 2**: Content (gpt-5.2-chat-latest) → 페이지별 narrative + widget JSON
4. **Step 3**: Translate (gpt-5.1-chat-latest) → 빈 영어 필드 번역 (선택)

### CLI 인터페이스
```bash
# 생성 모드 (3가지)
--generate "topic"           # 토픽으로 생성
--generate-from-event ID     # 기존 aggregate 이벤트 ID로 생성
--generate-from-person ID    # 인물 ID로 person_story 생성

# 임포트/번역/목록
--import FILE [--translate]  # YAML → DB
--translate-file FILE        # YAML 영어 번역
--list                       # DB 시프트 목록

# 옵션
--dry-run, --force, --model, --max-pages, --type
```

### DB 스키마 제약 준수
- `segment_has_entity`: 모든 페이지에 event_id/person_id/location_id/period_id 중 1개 필수
- `status`: user/cached/featured/system (draft 없음)
- `transition_type`: causes/follows/parallel/background/consequence/enables/opposes
- `transition_strength`: Integer 1-5
- Import 시 유효성 검사 포함

### 위젯 자동생성
15개 위젯 타입 전부 GPT 생성 가능:
primary_quote, faction_vs, dramatic_stat, person_card, battle_stats,
mini_timeline, era_context, narrator_aside, modern_equivalent,
what_if, historian_note, we_dont_know, conflicting_accounts,
territory_change, alliance_diagram

### YAML 중간 포맷
chapters → pages 구조. 각 page에 narrative + widgets + entity IDs.
사람이 검수 후 --import로 DB 삽입.

## 검증

- [x] Python 문법 검사 통과
- [x] `--help` 정상 출력
- [x] `--list` DB 연결 + 895개 시프트 목록 정상

## 다음 작업

- 실제 생성 테스트: `--generate "마라톤 전투" --type aggregate --dry-run`
- 임포트 테스트: 생성된 YAML → `--import --dry-run`
- 프론트엔드에서 시프트 재생 확인
