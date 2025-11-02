"""
Configuration management for Lexsy Document AI Backend
Production-ready environment handling
"""

import os
from dotenv import load_dotenv

# Load environment variables -PLACEHOLDER-env file
load_dotenv()


class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000'
    ).split(',')
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 50))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # LLM Configuration
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    # Document Processing
    SUPPORTED_FORMATS = ['docx']


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()


# Export config instance
config = get_config()
