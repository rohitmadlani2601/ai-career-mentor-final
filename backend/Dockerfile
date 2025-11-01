FROM python:3.9-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg libsm6 libxext6 libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Start Flask backend
CMD ["python", "backend/backend.py"]