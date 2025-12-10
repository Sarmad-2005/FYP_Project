FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application code
COPY services/api-gateway/ ./services/api-gateway/

# Expose port
EXPOSE 5000

# Run service
CMD ["python", "services/api-gateway/main.py"]
