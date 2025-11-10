#!/bin/bash
# Startup script for Railway deployment
# This script helps debug startup issues

echo "Starting application..."
echo "PORT=${PORT:-5001}"
echo "ENVIRONMENT=${ENVIRONMENT:-production}"
echo "Python path: $(which python)"
echo "Gunicorn path: $(which gunicorn)"

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "ERROR: app.py not found!"
    ls -la
    exit 1
fi

# Check if required modules can be imported
python -c "import flask; import flask_cors; print('Flask imports OK')" || {
    echo "ERROR: Flask imports failed!"
    exit 1
}

# Start gunicorn
exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 4 --timeout 120 --access-logfile - --error-logfile - app:app

