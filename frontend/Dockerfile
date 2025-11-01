# Use official lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && \
    pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Expose Streamlit default port
EXPOSE 8080

# Streamlit Cloud Run entrypoint
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]
