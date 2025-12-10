# Troubleshoot connection issues

Write-Host "=== Troubleshooting Connection Issues ===" -ForegroundColor Cyan
Write-Host ""

# Check if containers are running
Write-Host "1. Checking container status..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "2. Checking all Docker containers..." -ForegroundColor Yellow
docker ps -a

Write-Host ""
Write-Host "3. Checking if port 5000 is in use..." -ForegroundColor Yellow
$port5000 = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($port5000) {
    Write-Host "   Port 5000 is in use by:" -ForegroundColor Green
    $port5000 | Format-Table -AutoSize
} else {
    Write-Host "   Port 5000 is NOT in use - services may not be running" -ForegroundColor Red
}

Write-Host ""
Write-Host "4. Checking API Gateway logs..." -ForegroundColor Yellow
docker-compose logs --tail=20 api-gateway

Write-Host ""
Write-Host "5. Checking if services are starting..." -ForegroundColor Yellow
docker-compose logs --tail=10

Write-Host ""
Write-Host "=== Solutions ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If containers are not running, start them with:" -ForegroundColor Yellow
Write-Host "  docker-compose up -d" -ForegroundColor White
Write-Host ""
Write-Host "If containers are running but not accessible, check logs:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "To restart all services:" -ForegroundColor Yellow
Write-Host "  docker-compose restart" -ForegroundColor White
