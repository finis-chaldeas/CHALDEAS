@echo off
echo ============================================
echo C: 드라이브의 기존 PostgreSQL 데이터 삭제
echo ============================================
echo.
echo 주의: E:\PostgreSQL\data 로 이전이 완료된 후에만 실행하세요!
echo.
echo 삭제 대상: C:\Program Files\PostgreSQL\18\data
echo.
set /p confirm=정말 삭제하시겠습니까? (Y/N):
if /i "%confirm%" neq "Y" (
    echo 취소되었습니다.
    pause
    exit /b 0
)

echo.
echo 삭제 중...
rmdir /s /q "C:\Program Files\PostgreSQL\18\data"
if errorlevel 1 (
    echo 삭제 실패! 서비스가 실행 중이거나 권한이 없습니다.
    pause
    exit /b 1
)

echo.
echo ============================================
echo 삭제 완료! C: 드라이브 약 40GB 확보됨
echo ============================================
pause
