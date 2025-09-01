"""
Configuration for the OpenTAKServer API server
"""

import os

class Config:
    """Base configuration"""
    
    # Server settings
    HOST = os.getenv('OTS_LISTENER_ADDRESS', '0.0.0.0')
    PORT = int(os.getenv('OTS_LISTENER_PORT', 8080))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Database settings
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgresql')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'opentakserver')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'ots')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'changeme')
    
    # RabbitMQ settings
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'ots')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'changeme')
    RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', 'ots')
    
    # SSL settings
    SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/app/certs/server.pem')
    SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', '/app/certs/server-key.pem')
    
    # Data directory
    DATA_FOLDER = os.getenv('OTS_DATA_FOLDER', '/app/data')
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def RABBITMQ_URL(self):
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"