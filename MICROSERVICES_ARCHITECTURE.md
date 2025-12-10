# Microservices Architecture

## Overview
Single Docker image architecture with multiple microservices running via Docker Compose.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (Browser/Mobile)                    │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Main Flask App       │
            │   (Port 5001)          │
            │   - Dashboard UI       │
            │   - Project Management │
            └───────────┬─────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   API Gateway         │
            │   (Port 5000)         │
            │   - Route requests    │
            │   - Health checks     │
            └───────────┬─────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐       rag implemebtation
│  Financial   │ │ Performance  │ │ CSV Analysis │
│  Service     │ │ Service      │ │ Service      │
│  (Port 8001) │ │ (Port 8002)  │ │ (Port 8003)  │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ A2A Router   │ │  Scheduler   │ │   Shared     │
│ Service      │ │  Service     │ │   Resources  │
│ (Port 8004)  │ │ (Port 8005)  │ │ - ChromaDB   │
└──────────────┘ └──────────────┘ │ - Embeddings │
                                   └──────────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| **Main Flask App** | 5001 | Dashboard UI, project management |
| **API Gateway** | 5000 | Routes requests to microservices |
| **Financial Service** | 8001 | Financial analysis & transactions |
| **Performance Service** | 8002 | Tasks, milestones, bottlenecks, requirements, actors |
| **CSV Analysis Service** | 8003 | CSV file processing |
| **A2A Router Service** | 8004 | Agent-to-agent communication |
| **Scheduler Service** | 8005 | Background job scheduling |

## Docker Architecture

```
┌─────────────────────────────────────────────────┐
│         Single Docker Image                      │
│  (Multi-stage build, ~12.63 GB)                 │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Base: python:3.11-slim                   │  │
│  │  - All Python dependencies                │  │
│  │  - ChromaDB + Sentence Transformers      │  │
│  │  - Shared codebase                       │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  Entrypoint: docker-entrypoint.sh               │
│  - Routes to different services via command     │
└─────────────────────────────────────────────────┘
         │
         ├─── api-gateway
         ├─── financial-service
         ├─── performance-service
         ├─── csv-analysis-service
         ├─── a2a-router-service
         └─── scheduler-service
```

## Key Features

- **Single Image**: All services share one Docker image
- **Multi-stage Build**: Optimized for size
- **Shared Resources**: ChromaDB, embeddings, LLM manager
- **Service Isolation**: Each service runs in separate container
- **API Gateway**: Central routing point
- **Fallback Support**: Direct agent calls if gateway unavailable

## Communication Flow

1. Client → Main App (5001) → API Gateway (5000)
2. API Gateway → Target Service (8001-8005)
3. Services → Shared ChromaDB/Resources
4. Services ↔ A2A Router (inter-service communication)
