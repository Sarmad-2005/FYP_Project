# Docker Setup Guide - Microservices Architecture

## Prerequisites

1. **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux) installed
2. **Docker Compose** (usually included with Docker Desktop)
3. Verify installation:
   ```bash
   docker --version
   docker-compose --version
   ```

## Quick Start

### 1. Build All Images
```bash
cd proj
docker-compose build
```
This builds Docker images for all 6 services. Takes 5-10 minutes first time.

### 2. Start All Services
```bash
docker-compose up -d
```
The `-d` flag runs services in detached mode (background).

### 3. Check Service Status
```bash
docker-compose ps
```
All services should show "Up" status.

### 4. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-gateway
docker-compose logs -f financial-service
```

### 5. Access Services

Once running, access services at:

- **API Gateway (Main Entry Point)**: http://localhost:5000
  - Health: http://localhost:5000/health
  - Root: http://localhost:5000/

- **Financial Service**: http://localhost:8001
  - Health: http://localhost:8001/health

- **Performance Service**: http://localhost:8002
  - Health: http://localhost:8002/health

- **CSV Analysis Service**: http://localhost:8003
  - Health: http://localhost:8003/health

- **A2A Router Service**: http://localhost:8004
  - Health: http://localhost:8004/health

- **Scheduler Service**: http://localhost:8005
  - Health: http://localhost:8005/health

### 6. Stop All Services
```bash
docker-compose down
```

### 7. Stop and Remove Volumes (Clean Slate)
```bash
docker-compose down -v
```
⚠️ **Warning**: This removes all data volumes (ChromaDB, data files)

## Common Commands

### Restart a Specific Service
```bash
docker-compose restart api-gateway
```

### Rebuild and Restart
```bash
docker-compose up -d --build
```

### View Resource Usage
```bash
docker stats
```

### Execute Command in Container
```bash
docker-compose exec api-gateway python -c "print('Hello')"
```

### Check Service Health
```bash
# Check all health endpoints
curl http://localhost:5000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

## Troubleshooting

### Services Won't Start
1. Check logs: `docker-compose logs [service-name]`
2. Verify ports aren't in use: `netstat -an | findstr :5000`
3. Check Docker is running: `docker ps`

### Port Already in Use
If a port is already in use, either:
- Stop the conflicting service
- Or modify `docker-compose.yml` to use different ports

### Services Can't Communicate
- Verify all services are on `microservices-network`
- Check environment variables use Docker service names (e.g., `financial-service:8001`)

### Data Not Persisting
- Verify volume mounts in `docker-compose.yml`
- Check `./chroma_db` and `./data` directories exist

## Running the Dashboard (Old UI)

The old dashboard (`app.py`) is **NOT** containerized yet. To run it:

1. **In a separate terminal** (while Docker services are running):
   ```bash
   cd proj
   python app.py
   ```

2. Access at: http://localhost:5001

**Note**: The dashboard still uses the old monolithic architecture. It doesn't use the new microservices yet. This will be updated in Phase 8.

## Development Workflow

### Making Code Changes

1. **Edit code** in `proj/` directory
2. **Rebuild affected service**:
   ```bash
   docker-compose build financial-service
   docker-compose up -d financial-service
   ```

### Testing Changes

1. Run test scripts (outside Docker):
   ```bash
   python test_phase1.py
   python test_phase2.py
   # etc.
   ```

2. Or test via API Gateway:
   ```bash
   curl http://localhost:5000/financial_agent/health
   ```

## Production Considerations

For production deployment:

1. **Remove debug mode** from all services
2. **Use environment files** (`.env`) for secrets
3. **Set up reverse proxy** (nginx) in front of API Gateway
4. **Configure SSL/TLS** certificates
5. **Set up monitoring** (Prometheus, Grafana)
6. **Use Docker secrets** for sensitive data

## Next Steps

- **Phase 8**: Update UI to use API Gateway
- **Phase 9**: Migration strategy from monolithic to microservices
- **Phase 10**: Production deployment configuration
