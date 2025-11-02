"""
WSGI entry point for Gunicorn
This is what Gunicorn calls to run the application
"""
import sys
import os

# Add the backend directory to the Python path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    app.run()
