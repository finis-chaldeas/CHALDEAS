# 20260315 — Production Hardening

## 목적
상용 배포 기준 보안/관측성/성능/CI·CD/테스트 갭 해소.

## 변경 파일

### Phase 1: 보안 강화
- `backend/app/config.py` — CORS origins → `CORS_ORIGINS` 환경변수로 전환 (기본값 유지)
- `backend/app/main.py` — slowapi 글로벌 rate limiter (60/min), Sentry trace_id 포함 에러 응답
- `backend/app/api/v1/search.py` — 검색 엔드포인트 rate limit 20/min
- `backend/requirements.txt` — slowapi 추가
- `frontend/nginx.conf` — CSP, HSTS, Referrer-Policy, Permissions-Policy 헤더 추가

### Phase 2: 에러 처리 & 관측성
- `backend/app/main.py` — 모든 exception handler에 trace_id(uuid 8자리) 추가
- `frontend/src/api/client.ts` — `ApiError` 클래스 (status/code/traceId), 5xx만 Sentry 전송
- `frontend/src/components/common/ErrorBoundary.tsx` — componentDidCatch에서 Sentry.captureException
- `frontend/src/lib/sentry.tsx` — VITE_SENTRY_DSN만으로 초기화, PROD에서만 활성화

### Phase 3: 글로브 카메라 영속화
- `frontend/src/store/globeStore.ts` — Zustand persist 미들웨어, cameraPosition + cameraMode만 영속

### Phase 4: 번들 최적화
- `frontend/vite.config.ts` — three-core / three-globe 청크 분리

### Phase 5: CI/CD 강화
- `cloudbuild.yaml` — Step 0 frontend typecheck (tsc --noEmit) 추가
- `tools/pre-deploy-backup.ps1` — 배포 전 DB 백업 스크립트

### Phase 6: 테스트 기반
- `backend/tests/conftest.py` — TestClient fixture
- `backend/tests/test_api_smoke.py` — 8개 스모크 테스트 (5개 핵심 엔드포인트 + root + health + 404)
- `frontend/vitest.config.ts` — Vitest 설정
- `frontend/src/store/__tests__/timelineStore.test.ts` — 9개 스토어 단위 테스트
- `frontend/package.json` — vitest devDep, test/test:watch 스크립트

## 검증 결과
- `npx tsc --noEmit` — 통과
- `npx vitest run` — 9 passed (729ms)
- `pytest tests/test_api_smoke.py -v` — 8 passed (8.29s)
- Backend import 정상 (`from app.main import app`)

## 다음 작업
- Sentry DSN 설정 (프로덕션 .env에 VITE_SENTRY_DSN + SENTRY_DSN)
- `curl -I https://www.chaldeas.site` → 보안 헤더 검증 (배포 후)
- 프로덕션 배포: `gcloud builds submit --config=cloudbuild.yaml --project=chaldeas-archive`
