#!/bin/bash
# Docker entrypoint script for running different microservices

set -e  # Exit on error

SERVICE=$1
shift

# Change to app directory
cd /app

# Fix onnxruntime executable stack issue - disable it for chromadb
export ONNXRUNTIME_EXECUTION_PROVIDER=""
export PYTHONUNBUFFERED=1
export CHROMA_DISABLE_ONNXRUNTIME=1

case "$SERVICE" in
  api-gateway)
    exec python services/api-gateway/main.py
    ;;
  financial-service)
    exec python services/financial-service/main.py
    ;;
  performance-service)
    exec python services/performance-service/main.py
    ;;
  csv-analysis-service)
    exec python services/csv-analysis-service/main.py
    ;;
  a2a-router-service)
    exec python services/a2a-router-service/main.py
    ;;
  scheduler-service)
    exec python services/scheduler-service/main.py
    ;;
  risk-mitigation-service)
    exec python services/risk-mitigation-service/main.py
    ;;
  *)
    echo "Unknown service: $SERVICE"
    echo "Available services: api-gateway, financial-service, performance-service, csv-analysis-service, a2a-router-service, scheduler-service, risk-mitigation-service"
    exit 1
    ;;
esac
