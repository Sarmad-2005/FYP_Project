# Script to remove old service images and rebuild with single image

Write-Host "=== Rebuilding with Single Docker Image ===" -ForegroundColor Cyan
Write-Host ""

# Stop all containers
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "Removing old service images..." -ForegroundColor Yellow

# Remove old individual service images
$oldImages = @(
    "proj-api-gateway",
    "proj-financial-service",
    "proj-performance-service",
    "proj-csv-analysis-service",
    "proj-a2a-router-service",
    "proj-scheduler-service"
)

foreach ($image in $oldImages) {
    Write-Host "  Removing $image..." -ForegroundColor Green
    docker rmi "$image:latest" -f 2>$null
}

# Also remove any images with proj- prefix
Write-Host ""
Write-Host "Removing any remaining proj-* images..." -ForegroundColor Yellow
docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -like "proj-*" } | ForEach-Object {
    Write-Host "  Removing $_..." -ForegroundColor Green
    docker rmi $_ -f 2>$null
}

Write-Host ""
Write-Host "Building new single image..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Current images:" -ForegroundColor Yellow
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

Write-Host ""
Write-Host "To start services:" -ForegroundColor Cyan
Write-Host "  docker-compose up -d" -ForegroundColor White
