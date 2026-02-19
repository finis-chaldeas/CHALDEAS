@echo off
echo ============================================
echo PostgreSQL 데이터를 E: 드라이브로 이전
echo ============================================
echo.

echo [1/4] PostgreSQL 서비스 중지...
net stop postgresql-x64-18
if errorlevel 1 (
    echo 서비스 중지 실패. 이미 중지되었거나 권한이 없습니다.
    echo 관리자 권한으로 실행했는지 확인하세요.
    pause
    exit /b 1
)
echo 서비스 중지 완료!
echo.

echo [2/4] 데이터 복사 중... (약 5-10분 소요)
echo 원본: C:\Program Files\PostgreSQL\18\data
echo 대상: E:\PostgreSQL\data
xcopy "C:\Program Files\PostgreSQL\18\data" "E:\PostgreSQL\data\" /E /H /I /Y
if errorlevel 1 (
    echo 복사 실패!
    pause
    exit /b 1
)
echo 데이터 복사 완료!
echo.

echo [3/4] 서비스 설정 변경...
sc config postgresql-x64-18 binpath= "\"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe\" runservice -N \"postgresql-x64-18\" -D \"E:\PostgreSQL\data\" -w"
if errorlevel 1 (
    echo 설정 변경 실패!
    pause
    exit /b 1
)
echo 서비스 설정 완료!
echo.

echo [4/4] PostgreSQL 서비스 시작...
net start postgresql-x64-18
if errorlevel 1 (
    echo 서비스 시작 실패!
    pause
    exit /b 1
)
echo 서비스 시작 완료!
echo.

echo ============================================
echo 이전 완료!
echo 새 데이터 위치: E:\PostgreSQL\data
echo ============================================
pause
