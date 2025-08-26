import os

class Config:
    """Configuración base para Belgrano Tickets"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'belgrano_tickets_secret_2025'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de base de datos
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    
    # Configuración de Belgrano Ahorro
    BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL') or 'http://localhost:5000'
    
    # Configuración de Socket.IO
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # Configuración de puerto
    PORT = int(os.environ.get('PORT', 5001))

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    FLASK_ENV = 'production'

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
