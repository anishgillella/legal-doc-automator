#!/usr/bin/env python3
"""
Quick start script for backend2 API server
"""

import os
import sys

def main():
    """Run the Flask API server"""
    # Set default port if not specified
    if 'API_PORT' not in os.environ:
        os.environ['API_PORT'] = '5000'
    
    # Set default environment if not specified
    if 'ENVIRONMENT' not in os.environ:
        os.environ['ENVIRONMENT'] = 'development'
    
    print("=" * 60)
    print("Lexsy Document AI - Backend2 API Server")
    print("=" * 60)
    print(f"Starting server on port {os.environ['API_PORT']}...")
    print(f"Environment: {os.environ['ENVIRONMENT']}")
    print("=" * 60)
    print("\nAPI Endpoints:")
    print("  GET  /api/health        - Health check")
    print("  POST /api/process       - Detect placeholders")
    print("  POST /api/fill          - Fill placeholders")
    print("  POST /api/placeholders  - Get placeholders only")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Import and run the app
    from app import app
    
    port = int(os.environ['API_PORT'])
    debug_mode = os.environ['ENVIRONMENT'] == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

