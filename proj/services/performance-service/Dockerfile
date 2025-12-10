FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY services/performance-service/ ./services/performance-service/
COPY backend/ ./backend/
COPY shared/ ./shared/

# Expose port
EXPOSE 8002

# Run service
CMD ["python", "services/performance-service/main.py"]
