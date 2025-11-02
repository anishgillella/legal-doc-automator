FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and Flask
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 8000

# Test basic Flask app first
RUN python << 'EOF'
from flask import Flask
test_app = Flask(__name__)

@test_app.route('/test')
def test():
    return {'status': 'ok'}

print("✓ Flask app can be created")
EOF

# Set Python path
ENV PYTHONPATH=/app

# Run the actual app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--log-level", "info", "backend.app:app"]
