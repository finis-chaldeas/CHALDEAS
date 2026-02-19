# Wikidata 전체 덤프 다운로드 스크립트
# 크기: ~93GB (bz2) 또는 ~141GB (gz)

$DUMP_URL = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2"
$OUTPUT_FILE = "C:\Projects\Chaldeas\data\wikidata\latest-all.json.bz2"

Write-Host "=== Wikidata Dump 다운로드 ===" -ForegroundColor Cyan
Write-Host "URL: $DUMP_URL"
Write-Host "출력: $OUTPUT_FILE"
Write-Host "예상 크기: ~93 GB"
Write-Host ""

# aria2c 사용 (더 빠름)
if (Get-Command aria2c -ErrorAction SilentlyContinue) {
    Write-Host "aria2c로 다운로드 중... (병렬 연결)"
    aria2c --max-connection-per-server=16 --split=16 --continue=true -d "C:\Projects\Chaldeas\data\wikidata" -o "latest-all.json.bz2" $DUMP_URL
}
# curl 사용
elseif (Get-Command curl -ErrorAction SilentlyContinue) {
    Write-Host "curl로 다운로드 중..."
    curl -L -C - -o $OUTPUT_FILE $DUMP_URL
}
# PowerShell 기본
else {
    Write-Host "PowerShell로 다운로드 중... (느릴 수 있음)"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $DUMP_URL -OutFile $OUTPUT_FILE -Resume
}

Write-Host ""
Write-Host "다운로드 완료!" -ForegroundColor Green
Write-Host "파일: $OUTPUT_FILE"
