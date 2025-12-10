# Multi-stage build to reduce final image size
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage - minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# PATCH chromadb to use sentence-transformers instead of onnxruntime
RUN sed -i 's/return ONNXMiniLM_L6_V2()/return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")/' /root/.local/lib/python3.11/site-packages/chromadb/utils/embedding_functions.py || true

ENV ONNXRUNTIME_EXECUTION_PROVIDER=""

# Copy application code
COPY services/ ./services/
COPY backend/ ./backend/
COPY shared/ ./shared/

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    sed -i 's/\r$//' /entrypoint.sh && \
    head -1 /entrypoint.sh

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
