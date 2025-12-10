FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY services/csv-analysis-service/ ./services/csv-analysis-service/
COPY backend/ ./backend/
COPY shared/ ./shared/

# Expose port
EXPOSE 8003

# Run service
CMD ["python", "services/csv-analysis-service/main.py"]
