# Script to build single Docker image and start all services

Write-Host "=== Building Single Docker Image ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will take 5-10 minutes as it downloads dependencies..." -ForegroundColor Yellow
Write-Host ""

# Build the single image
docker-compose build

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host ""

# Show the new image
Write-Host "New Docker image:" -ForegroundColor Yellow
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

Write-Host ""
Write-Host "=== Starting All Services ===" -ForegroundColor Cyan
Write-Host ""

# Start all services
docker-compose up -d

Write-Host ""
Write-Host "=== Service Status ===" -ForegroundColor Cyan
Write-Host ""

# Wait a moment for services to start
Start-Sleep -Seconds 3

# Show service status
docker-compose ps

Write-Host ""
Write-Host "=== Service Health Checks ===" -ForegroundColor Cyan
Write-Host ""

# Check health of each service
$services = @(
    @{Name="API Gateway"; Port=5000},
    @{Name="Financial Service"; Port=8001},
    @{Name="Performance Service"; Port=8002},
    @{Name="CSV Analysis Service"; Port=8003},
    @{Name="A2A Router Service"; Port=8004},
    @{Name="Scheduler Service"; Port=8005}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($service.Name) (port $($service.Port))" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [WAIT] $($service.Name) (port $($service.Port)) - starting..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "All services are starting. Check status with:" -ForegroundColor Yellow
Write-Host "  docker-compose ps" -ForegroundColor White
Write-Host ""
Write-Host "View logs with:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "Access services at:" -ForegroundColor Yellow
Write-Host "  API Gateway: http://localhost:5000" -ForegroundColor White
Write-Host "  Financial: http://localhost:8001" -ForegroundColor White
Write-Host "  Performance: http://localhost:8002" -ForegroundColor White
