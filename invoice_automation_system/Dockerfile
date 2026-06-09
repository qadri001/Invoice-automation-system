FROM python:3.9-slim

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install paddlepaddle paddleocr

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/invoices data/processed data/database logs temp_images

# Expose ports for API and Dashboard
EXPOSE 8000 8501

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV OCR_ENGINE=paddleocr

# Default command (can be overridden)
CMD ["python", "run.py", "--watch"]
