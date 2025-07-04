import os

class Config:
        """Base configuration class."""
        SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_should_be_changed_in_production'
        MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/mindease_db'
        # Set this to False in production
        DEBUG = True
        TESTING = False
        # Add any other configuration variables here

class DevelopmentConfig(Config):
        """Development specific configuration."""
        DEBUG = True

class ProductionConfig(Config):
        """Production specific configuration."""
        DEBUG = False
        TESTING = False
        # Ensure SECRET_KEY and MONGO_URI are set as environment variables in production
    