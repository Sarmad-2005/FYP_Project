FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY services/scheduler-service/ ./services/scheduler-service/
COPY backend/ ./backend/
COPY shared/ ./shared/

# Expose port
EXPOSE 8005

# Run service
CMD ["python", "services/scheduler-service/main.py"]
