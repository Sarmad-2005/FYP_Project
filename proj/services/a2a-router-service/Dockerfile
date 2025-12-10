FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY services/a2a-router-service/ ./services/a2a-router-service/
COPY backend/ ./backend/
COPY shared/ ./shared/

# Expose port
EXPOSE 8004

# Run service
CMD ["python", "services/a2a-router-service/main.py"]
