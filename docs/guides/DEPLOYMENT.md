# CHALDEAS 배포 운영 가이드

## 개요

CHALDEAS는 GCP Cloud Run + Cloud SQL로 운영된다.
이 문서는 **실제 배포 절차**를 순서대로 정리한 운영 매뉴얼이다.

---

## 아키텍처

```
www.chaldeas.site (CNAME → ghs.googlehosted.com)
       │
       ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  Cloud Run (Frontend)   │        │  Cloud Run (Backend)    │
│  us-central1            │──API──▶│  asia-northeast3        │
│  nginx + SPA            │        │  FastAPI + gunicorn     │
│  512Mi / 0-3 instances  │        │  1Gi / 0-5 instances    │
└─────────────────────────┘        └──────────┬──────────────┘
                                              │
                                   ┌──────────▼──────────────┐
                                   │  Cloud SQL (PostgreSQL) │
                                   │  asia-northeast3        │
                                   │  db-g1-small + pgvector │
                                   │  ~2.2GB                 │
                                   └─────────────────────────┘
```

| 항목 | 값 |
|------|-----|
| GCP Project | `chaldeas-archive` |
| Frontend Region | `us-central1` (도메인 매핑 필수) |
| Backend Region | `asia-northeast3` |
| Cloud SQL Instance | `chaldeas-db` |
| Artifact Registry | `asia-northeast3-docker.pkg.dev/chaldeas-archive/chaldeas` |
| GCS Bucket (DB sync) | `gs://chaldeas-archive-db-sync` |
| 도메인 | `www.chaldeas.site` |

---

## 배포 시나리오별 절차

### A. 코드만 변경 (프론트엔드/백엔드)

DB 변경 없이 코드만 배포할 때.

```powershell
# 프로젝트 루트에서 실행
# 전체 배포 (Backend → Frontend 순서, ~15분)
.\scripts\deploy.ps1 all

# 또는 개별 배포
.\scripts\deploy.ps1 backend    # 백엔드만 (~7분)
.\scripts\deploy.ps1 frontend   # 프론트엔드만 (~7분)
```

내부 동작:
1. Docker 빌드 (Dockerfile.prod)
2. Artifact Registry에 push
3. Cloud Run에 새 revision 배포
4. 프론트엔드는 asia-northeast3 + us-central1 양쪽 배포

### B. 데이터 변경 (DB 동기화)

로컬 DB 데이터를 클라우드로 올릴 때. **전체 교체 방식**.

```powershell
# 1. 로컬 DB가 Compact(C:\PostgreSQL\data)인지 확인
.\tools\switch-db.ps1 status

# 2. DB 동기화 (Local → Cloud)
.\scripts\sync-db.ps1 up
```

내부 동작:
1. `pg_dump` 로컬 DB → SQL 파일 (~2.2GB, data-only)
2. 비호환 SET 명령 필터링
3. GCS 버킷에 업로드
4. `gcloud sql import sql`로 Cloud SQL에 import
5. 권한 GRANT (Cloud SQL Proxy 사용)
6. 임시 파일 정리

**예상 시간**: ~15-20분 (dump 3분 + 업로드 5분 + import 10분)
**주의**: Cloud SQL import는 기존 데이터를 덮어쓴다 (INSERT, ON CONFLICT 없음)

### C. 스키마 변경 (마이그레이션)

테이블 구조가 바뀔 때. **sync-db.ps1 전에 해야 한다.**

```powershell
# 1. Cloud SQL Proxy 실행 (별도 터미널)
C:\tools\cloud-sql-proxy.exe chaldeas-archive:asia-northeast3:chaldeas-db --port=5433

# 2. 마이그레이션 실행
cd backend
$env:DATABASE_URL = "postgresql://postgres:postgres_gcp_2025@localhost:5433/chaldeas"
python -m alembic upgrade head

# 또는 수동 ALTER
$env:PGPASSWORD = "postgres_gcp_2025"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5433 -d chaldeas -c "ALTER TABLE entity_narratives ALTER COLUMN significance TYPE TEXT;"
```

### D. 전체 배포 (코드 + DB + 스키마)

가장 일반적인 배포 시나리오. 순서가 중요하다.

```powershell
# Step 1: 스키마 변경이 있으면 먼저 Cloud SQL에 적용
#   (위 C 절차 따라)

# Step 2: DB 데이터 동기화
.\scripts\sync-db.ps1 up

# Step 3: 코드 배포
.\scripts\deploy.ps1 all

# Step 4: 확인
.\scripts\deploy.ps1 status
```

**순서 규칙:**
```
스키마 변경 → DB 동기화 → 백엔드 배포 → 프론트엔드 배포
```

스키마를 먼저 바꿔야 데이터가 들어가고, 백엔드를 먼저 배포해야 프론트엔드가 새 API를 사용할 수 있다.

---

## 로컬 DB 관리

### Compact vs Archive

| DB | 경로 | 크기 | 용도 |
|----|------|------|------|
| Compact | `C:\PostgreSQL\data` | ~2.2GB | 개발/배포 (SSD) |
| Archive | `E:\PostgreSQL\data` | 44GB | 전체 Wikidata (HDD) |

```powershell
.\tools\switch-db.ps1 compact    # Compact 사용
.\tools\switch-db.ps1 archive    # Archive 사용
.\tools\switch-db.ps1 status     # 현재 상태
```

### Compact DB 재구축 (Archive → Compact)

Archive에서 필요한 데이터만 추출:

```powershell
.\tools\switch-db.ps1 archive
cd backend
python scripts/export_compact.py      # CSV 추출 → data/compact_export/
.\tools\switch-db.ps1 compact
python -m alembic upgrade head        # 스키마 생성
python scripts/import_compact.py      # CSV 임포트
```

---

## 현재 스키마 변경 이력 (Alembic 외)

sync-db.ps1은 data-only dump이므로 스키마 변경은 별도로 적용해야 한다.
아래는 Alembic 마이그레이션 없이 직접 ALTER한 내역:

```sql
-- 2026-02-24: significance 컬럼 VARCHAR(500) → TEXT 확장
ALTER TABLE entity_narratives ALTER COLUMN significance TYPE TEXT;
ALTER TABLE entity_narratives ALTER COLUMN significance_ko TYPE TEXT;
ALTER TABLE entity_narratives ALTER COLUMN significance_ja TYPE TEXT;
```

**배포 전 Cloud SQL에 이 ALTER를 먼저 실행해야 한다.**

---

## 검증 체크리스트

### 배포 후 확인

```powershell
# 1. 서비스 URL 확인
.\scripts\deploy.ps1 status

# 2. 백엔드 헬스체크
curl https://chaldeas-backend-951004107180.asia-northeast3.run.app/health

# 3. API 응답 확인
curl "https://chaldeas-backend-951004107180.asia-northeast3.run.app/api/v1/events?limit=3"

# 4. 프론트엔드 접속
# 브라우저에서 https://www.chaldeas.site 열기

# 5. DB 동기화 상태 비교
.\scripts\sync-db.ps1 status
```

### DB 동기화 후 확인 (Cloud SQL Proxy 필요)

```powershell
# Cloud SQL Proxy 실행 (별도 터미널)
C:\tools\cloud-sql-proxy.exe chaldeas-archive:asia-northeast3:chaldeas-db --port=5433

# 주요 테이블 row count 비교
$env:PGPASSWORD = "postgres_gcp_2025"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5433 -d chaldeas -c "
    SELECT 'events' as t, COUNT(*) FROM events
    UNION ALL SELECT 'persons', COUNT(*) FROM persons
    UNION ALL SELECT 'locations', COUNT(*) FROM locations
    UNION ALL SELECT 'entity_narratives', COUNT(*) FROM entity_narratives
    ORDER BY t;
"
```

---

## 트러블슈팅

### Cloud SQL import 실패

```
ERROR: duplicate key value violates unique constraint
```

→ Cloud SQL에 기존 데이터가 있으면 충돌. 전체 TRUNCATE 후 재시도:

```powershell
# Cloud SQL Proxy 연결 후
psql -U postgres -h localhost -p 5433 -d chaldeas -c "
    DO \$\$ DECLARE r RECORD;
    BEGIN
        FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
            EXECUTE 'TRUNCATE TABLE ' || r.tablename || ' CASCADE';
        END LOOP;
    END \$\$;
"
# 그 다음 sync-db.ps1 up 재실행
```

### Cold Start 느림 (첫 요청 5-10초)

```powershell
# 최소 인스턴스 1개 유지 (월 ~$15 추가)
gcloud run services update chaldeas-backend --min-instances=1 --region=asia-northeast3
```

### Cloud SQL Proxy 없음

```powershell
# 다운로드: https://cloud.google.com/sql/docs/postgres/sql-proxy
# 설치 경로: C:\tools\cloud-sql-proxy.exe
# 인증: gcloud auth application-default login
```

### Cloud SQL 인스턴스 중지/시작 (비용 절감)

```powershell
gcloud sql instances patch chaldeas-db --activation-policy=NEVER    # 중지
gcloud sql instances patch chaldeas-db --activation-policy=ALWAYS   # 시작
```

---

## 스크립트 정리

| 스크립트 | 용도 | 사용 시점 |
|----------|------|-----------|
| `scripts/deploy.ps1 all` | 코드 배포 (Cloud Build) | 코드 변경 후 |
| `scripts/deploy.ps1 backend` | 백엔드만 배포 | API 변경 후 |
| `scripts/deploy.ps1 frontend` | 프론트엔드만 배포 | UI 변경 후 |
| `scripts/sync-db.ps1 up` | 로컬 DB → Cloud SQL | 데이터 변경 후 |
| `scripts/sync-db.ps1 down` | Cloud SQL → 로컬 DB | 클라우드 데이터 받기 |
| `scripts/sync-db.ps1 status` | DB 비교 | 동기화 상태 확인 |
| `scripts/gcp-setup.ps1` | GCP 초기 설정 | 최초 1회 |
| `tools/switch-db.ps1` | Compact/Archive DB 전환 | DB 전환 시 |

---

## 비용

| 서비스 | 스펙 | 월 예상 |
|--------|------|---------|
| Cloud Run Backend | 1 vCPU, 1GB, 0-5 inst | $15-30 |
| Cloud Run Frontend | 1 vCPU, 512MB, 0-3 inst | $8-15 |
| Cloud SQL | db-g1-small, 10GB SSD | $25-35 |
| 기타 (GCS, Secrets, Registry) | - | ~$1 |
| **합계** | | **$49-81/월** |
| **Free Tier 활용 시** | | **$10-30/월** |

### 비용 절감 팁
- `min-instances=0` 유지 (cold start 감수)
- 사용 안 할 때 Cloud SQL 중지: `--activation-policy=NEVER`
- 프론트엔드 CDN 연결 시 Cloud Run Frontend 비용 절감 가능
