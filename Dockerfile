FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg and CA certificates for SSL
RUN apt-get update && apt-get install -y ffmpeg ca-certificates && update-ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r snaptube-clone/requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp certifi

# Use the threading-based web_app (no timeout limits)
WORKDIR /app/snaptube-clone

# Hugging Face Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

# Run with gunicorn + threads for background downloads
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 web_app:app
