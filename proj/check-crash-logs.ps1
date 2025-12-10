# Check why services are crashing

Write-Host "=== Checking Service Crash Logs ===" -ForegroundColor Cyan
Write-Host ""

# Check each service's logs
$services = @("api-gateway", "financial-service", "performance-service", "csv-analysis-service", "a2a-router-service", "scheduler-service")

foreach ($service in $services) {
    Write-Host "=== $service Logs ===" -ForegroundColor Yellow
    docker-compose logs --tail=10 $service
    Write-Host ""
}

Write-Host "=== Checking if image exists ===" -ForegroundColor Cyan
docker images | Select-String "proj"

Write-Host ""
Write-Host "=== Testing entrypoint manually ===" -ForegroundColor Cyan
Write-Host "Trying to run a test command in api-gateway container..."
docker-compose run --rm api-gateway /bin/bash -c "ls -la /entrypoint.sh && cat /entrypoint.sh" 2>&1
