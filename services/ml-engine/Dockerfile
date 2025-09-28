# TuneTrail ML Engine Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create model directories
RUN mkdir -p /models/free /models/starter /models/pro /models/enterprise /models/faiss_indexes

EXPOSE 8001

# Run the ML engine service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]