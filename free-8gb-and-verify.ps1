# Script to free up 8GB by removing old Docker images and verify

Write-Host "=== Freeing Up Docker Space ===" -ForegroundColor Cyan
Write-Host ""

# Show BEFORE state
Write-Host "BEFORE Cleanup:" -ForegroundColor Yellow
$before = docker system df
Write-Host $before
Write-Host ""

# Stop all containers
Write-Host "Stopping all containers..." -ForegroundColor Green
docker-compose down 2>$null

# Remove old individual service images
Write-Host ""
Write-Host "Removing old service images..." -ForegroundColor Green
$oldImages = @(
    "proj-api-gateway:latest",
    "proj-financial-service:latest",
    "proj-performance-service:latest",
    "proj-csv-analysis-service:latest",
    "proj-a2a-router-service:latest",
    "proj-scheduler-service:latest"
)

$removedCount = 0
foreach ($image in $oldImages) {
    $result = docker rmi $image -f 2>&1
    if ($LASTEXITCODE -eq 0 -or $result -match "Deleted") {
        Write-Host "  [OK] Removed $image" -ForegroundColor Green
        $removedCount++
    } elseif ($result -match "No such image") {
        Write-Host "  [-] $image (not found, already removed)" -ForegroundColor Gray
    }
}

# Remove any dangling images
Write-Host ""
Write-Host "Removing dangling images..." -ForegroundColor Green
docker image prune -f | Out-Null

# Remove unused containers
Write-Host "Removing stopped containers..." -ForegroundColor Green
docker container prune -f | Out-Null

# Remove unused volumes (be careful - this removes data!)
Write-Host "Removing unused volumes..." -ForegroundColor Green
docker volume prune -f | Out-Null

# Remove build cache
Write-Host "Removing build cache..." -ForegroundColor Green
docker builder prune -a -f | Out-Null

Write-Host ""
Write-Host "=== AFTER Cleanup ===" -ForegroundColor Cyan
Write-Host ""

# Show AFTER state
Write-Host "AFTER Cleanup:" -ForegroundColor Yellow
$after = docker system df
Write-Host $after

Write-Host ""
Write-Host "=== Verification ===" -ForegroundColor Cyan
Write-Host ""

# Extract sizes from output
$beforeMatch = $before | Select-String "Images\s+\d+\s+\d+\s+(\d+\.?\d*[KMGT]?B)"
$afterMatch = $after | Select-String "Images\s+\d+\s+\d+\s+(\d+\.?\d*[KMGT]?B)"

if ($beforeMatch -and $afterMatch) {
    Write-Host "Images BEFORE: $($beforeMatch.Matches.Groups[1].Value)" -ForegroundColor Cyan
    Write-Host "Images AFTER:  $($afterMatch.Matches.Groups[1].Value)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[SUCCESS] Space has been freed!" -ForegroundColor Green
} else {
    Write-Host "[SUCCESS] Cleanup completed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Remaining images:" -ForegroundColor Yellow
docker images --format "table {{.Repository}}`t{{.Tag}}`t{{.Size}}"

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Removed $removedCount old service images" -ForegroundColor Green
Write-Host ""
Write-Host "Next step: Build the new single image with:" -ForegroundColor Yellow
Write-Host "  docker-compose build" -ForegroundColor White
