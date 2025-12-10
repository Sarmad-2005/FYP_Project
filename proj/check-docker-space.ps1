# Script to check what's using Docker space

Write-Host "=== Docker Space Analysis ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Docker System Summary:" -ForegroundColor Yellow
docker system df

Write-Host ""
Write-Host "Detailed Image List:" -ForegroundColor Yellow
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

Write-Host ""
Write-Host "Containers:" -ForegroundColor Yellow
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Size}}"

Write-Host ""
Write-Host "Volumes:" -ForegroundColor Yellow
docker volume ls

Write-Host ""
Write-Host "Build Cache:" -ForegroundColor Yellow
docker builder du

Write-Host ""
Write-Host "=== Breakdown ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To see detailed breakdown:" -ForegroundColor Yellow
Write-Host "  docker system df -v" -ForegroundColor White
Write-Host ""
Write-Host "To find Docker data location:" -ForegroundColor Yellow
Write-Host "  docker info | findstr 'Docker Root Dir'" -ForegroundColor White
