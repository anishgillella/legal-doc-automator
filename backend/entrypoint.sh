#!/bin/bash
# Entrypoint script to handle dynamic PORT variable expansion for Railway

# Default to 5000 if PORT is not set
PORT=${PORT:-5000}

# Run gunicorn with the expanded PORT variable
exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app
