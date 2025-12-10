# Docker Cleanup Script for Windows PowerShell
# This script removes old Docker images and frees up disk space

Write-Host "=== Docker Cleanup Script ===" -ForegroundColor Cyan
Write-Host ""

# Show current disk usage
Write-Host "Current Docker disk usage:" -ForegroundColor Yellow
docker system df

Write-Host ""
Write-Host "Removing old/unused images..." -ForegroundColor Yellow

# Remove all stopped containers
Write-Host "Removing stopped containers..." -ForegroundColor Green
docker container prune -f

# Remove all unused images (not just dangling)
Write-Host "Removing unused images..." -ForegroundColor Green
docker image prune -a -f

# Remove unused volumes
Write-Host "Removing unused volumes..." -ForegroundColor Green
docker volume prune -f

# Remove build cache
Write-Host "Removing build cache..." -ForegroundColor Green
docker builder prune -a -f

Write-Host ""
Write-Host "=== Cleanup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Updated Docker disk usage:" -ForegroundColor Yellow
docker system df

Write-Host ""
Write-Host "To remove specific old images, run:" -ForegroundColor Cyan
Write-Host "  docker rmi <image_id>" -ForegroundColor White
Write-Host ""
Write-Host "To see all images:" -ForegroundColor Cyan
Write-Host "  docker images" -ForegroundColor White
