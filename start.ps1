# BinBaz App — Unified Startup Script
# Run from the ibn-baz root: .\start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   مكتبة الشيخ ابن باز — Starting App   " -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Kill anything already on ports 8002 / 3000
foreach ($port in 8002, 3000) {
    $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess
    if ($proc) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
        Write-Host "  Cleared port $port (PID $proc)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "  Starting backend  (http://localhost:8002) ..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\backend'; uvicorn api.main:app --reload --host 0.0.0.0 --port 8002" `
    -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "  Starting frontend (http://localhost:3000) ..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\frontend'; `$env:NODE_OPTIONS='--openssl-legacy-provider'; npm run build; npm run start" `
    -WindowStyle Normal


Write-Host ""
Write-Host "  Both services started in separate windows." -ForegroundColor Cyan
Write-Host "  Backend  → http://localhost:8002" -ForegroundColor White
Write-Host "  Frontend → http://localhost:3000" -ForegroundColor White
Write-Host ""
