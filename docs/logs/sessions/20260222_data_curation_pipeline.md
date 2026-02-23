# 세션 로그: 2026-02-22 Data Curation Pipeline 구현

## 세션 정보
- **목적**: Compact DB 기준 데이터 재큐레이션 파이프라인 구현
- **소스 3종**: Wikipedia(기존) + Gutenberg(기존 Book Extractor) + 새 인터넷 검색 소스

## 구현한 파일

### NEW 파일
| 파일 | 설명 |
|------|------|
| `poc/scripts/extract_from_archive.py` | Archive DB → CSV 추출 (content_raw, narratives, mentions, properties) |
| `poc/scripts/import_archive_data.py` | CSV → Compact DB 임포트 (UPDATE/INSERT) |
| `poc/scripts/cleanup_phase2.py` | 4-step 정리 (고아 인물, role 버그, 중복 이벤트, 언어 오염) |

### MODIFIED 파일
| 파일 | 변경 사항 |
|------|-----------|
| `poc/scripts/curate_with_llm.py` | `--min-importance`, `--skip-existing` 추가, 영어 전용 프롬프트, 소스 3000자 제한 |
| `backend/scripts/export_compact.py` | entity_narratives, text_mentions, entity_properties, person_sources, person_detail 추가 |
| `backend/scripts/import_compact.py` | 같은 테이블들 import 순서에 추가, 시퀀스 리셋 목록에 추가 |

## 실행 순서

```
Phase 1: Archive → CSV → Compact
  1. .\tools\switch-db.ps1 archive
  2. python poc/scripts/extract_from_archive.py --dry-run  (확인)
  3. python poc/scripts/extract_from_archive.py             (추출)
  4. .\tools\switch-db.ps1 compact
  5. python poc/scripts/import_archive_data.py --dry-run    (확인)
  6. python poc/scripts/import_archive_data.py               (임포트)

Phase 1.5: Gutenberg 원문 추출 (기존 Book Extractor 사용)
  - tools/book_extractor/ 서버 + 대시보드
  - 역사 관련 핵심 책 50-100권 대상

Phase 1.7: 인터넷 검색 소스 확보 (주요 인물/이벤트)
  - 학술 논문, 1차 사료, 책 전문 등 신뢰할 수 있는 자료
  - 단순 기사 제외
  - DB에 source로 적재

Phase 2: 데이터 정리
  python poc/scripts/cleanup_phase2.py --dry-run   (미리보기)
  python poc/scripts/cleanup_phase2.py              (실행)

Phase 3: GPT-5.1 큐레이션 (비용 발생 - 사전 보고 필요!)
  - 예상 비용: ~$21
  - 사전에 사용자 승인 필요
  python poc/scripts/curate_with_llm.py --step 0
  python poc/scripts/curate_with_llm.py --step 1 --min-importance 2 --skip-existing
  python poc/scripts/curate_with_llm.py --step 2 --skip-existing
  python poc/scripts/curate_with_llm.py --step 3 --skip-existing
  python poc/scripts/curate_with_llm.py --step 5 --min-importance 2 --skip-existing

Phase 4: Export/Import 스크립트 업데이트 (완료)
```

## 결과
- 6개 파일 생성/수정 완료
- 모든 스크립트 --dry-run 모드 지원
- GPT 비용 발생 단계 전 사용자 보고 규칙 적용

## 다음 작업
- Phase 1 실행 (DB 전환 + 추출 + 임포트)
- Phase 1.7 인터넷 소스 검색 스크립트 구현
- Phase 2 dry-run 후 실행
- Phase 3 전 비용 보고
