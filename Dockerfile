FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg for audio conversion
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the api app (the Vercel-compatible server)
COPY api/ api/
COPY requirements.txt .

# Set working directory to api for proper imports
WORKDIR /app/api

# Expose port
EXPOSE 10000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "4", "--timeout", "300", "index:app"]