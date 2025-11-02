FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 8000

# Set Python path so backend package can be found
ENV PYTHONPATH=/app

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--log-level", "info", "backend.app:app"]
