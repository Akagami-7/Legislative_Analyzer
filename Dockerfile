# Use official Python 3.11 slim image for a lightweight base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set the working directory
WORKDIR /app

# Install system dependencies (Tesseract OCR, Poppler for PDFs, and build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# We explicitly install the CPU version of PyTorch first. This is CRITICAL for self-hosting 
# because the default PyTorch installs massive CUDA (GPU) libraries that bloat the container by ~4GB.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Download the required spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY . .

# Expose the API and Dashboard port
EXPOSE 8000

# Start the FastAPI server
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
