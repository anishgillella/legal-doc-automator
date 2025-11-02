FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy entire application first
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run gunicorn from backend directory
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
