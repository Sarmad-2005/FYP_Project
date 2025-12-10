# How to Access Your Microservices System

## 🚀 Quick Access

### Main Entry Point (API Gateway)
**URL:** http://localhost:5000

### Check System Status
**URL:** http://localhost:5000/health

This shows the health of all services.

### View Available Routes
**URL:** http://localhost:5000/

This shows all available API routes.

---

## 📍 Service Endpoints

### 1. Financial Service
**Base URL:** http://localhost:5000/financial_agent

**Key Endpoints:**
- `POST /financial_agent/first_generation` - Generate financial data for a project
- `POST /financial_agent/refresh/<project_id>` - Refresh financial data
- `GET /financial_agent/status/<project_id>` - Get financial status
- `GET /financial_agent/health` - Health check

**Direct Access:** http://localhost:8001

### 2. Performance Service
**Base URL:** http://localhost:5000/performance_agent

**Key Endpoints:**
- `POST /performance_agent/first_generation` - Generate performance metrics
- `POST /performance_agent/refresh/<project_id>` - Refresh performance data
- `GET /performance_agent/status/<project_id>` - Get performance status
- `GET /performance_agent/health` - Health check

**Direct Access:** http://localhost:8002

### 3. CSV Analysis Service
**Base URL:** http://localhost:5000/csv_analysis

**Key Endpoints:**
- `POST /csv_analysis/upload` - Upload CSV file
- `POST /csv_analysis/ask` - Ask questions about CSV data
- `GET /csv_analysis/data` - Get CSV data
- `GET /csv_analysis/health` - Health check

**Direct Access:** http://localhost:8003

### 4. A2A Router Service
**Base URL:** http://localhost:5000/a2a_router

**Key Endpoints:**
- `POST /a2a_router/register` - Register an agent
- `POST /a2a_router/send` - Send A2A message
- `GET /a2a_router/health` - Health check

**Direct Access:** http://localhost:8004

### 5. Scheduler Service
**Base URL:** http://localhost:5000/scheduler

**Key Endpoints:**
- `GET /scheduler/health` - Health check
- `GET /scheduler/status` - Get scheduler status

**Direct Access:** http://localhost:8005

---

## 🧪 Test Your System

### Option 1: Using Browser

1. **Check if system is running:**
   ```
   http://localhost:5000/health
   ```

2. **View API information:**
   ```
   http://localhost:5000/
   ```

### Option 2: Using PowerShell/curl

```powershell
# Check health
Invoke-WebRequest -Uri "http://localhost:5000/health" | Select-Object -ExpandProperty Content

# View API info
Invoke-WebRequest -Uri "http://localhost:5000/" | Select-Object -ExpandProperty Content

# Test Financial Service
Invoke-WebRequest -Uri "http://localhost:8001/health" | Select-Object -ExpandProperty Content
```

### Option 3: Using Python

```python
import requests

# Check health
response = requests.get("http://localhost:5000/health")
print(response.json())

# View API info
response = requests.get("http://localhost:5000/")
print(response.json())
```

---

## 📊 Example API Calls

### Example 1: Financial Agent - First Generation
```powershell
$body = @{
    project_id = "your-project-id"
    document_id = "your-document-id"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/financial_agent/first_generation" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### Example 2: CSV Analysis - Upload
```powershell
$filePath = "path/to/your/file.csv"
$projectId = "your-project-id"

$formData = @{
    file = Get-Item $filePath
    project_id = $projectId
}

Invoke-WebRequest -Uri "http://localhost:5000/csv_analysis/upload" `
    -Method POST `
    -Form $formData
```

---

## 🔍 Troubleshooting

### Check if services are running:
```powershell
docker-compose ps
```

### View logs:
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-gateway
docker-compose logs -f financial-service
```

### Restart a service:
```powershell
docker-compose restart api-gateway
```

### Check service health individually:
- http://localhost:8001/health (Financial)
- http://localhost:8002/health (Performance)
- http://localhost:8003/health (CSV Analysis)
- http://localhost:8004/health (A2A Router)
- http://localhost:8005/health (Scheduler)

---

## 🎯 Quick Start Checklist

- [ ] Services are running: `docker-compose ps`
- [ ] API Gateway is accessible: http://localhost:5000
- [ ] Health check works: http://localhost:5000/health
- [ ] All services show "healthy" in health check response

---

## 📝 Notes

- **API Gateway** (port 5000) is the main entry point - use this for all requests
- Individual services are also accessible directly on ports 8001-8005
- All routes are proxied through the gateway automatically
- CORS is enabled, so you can access from web browsers
