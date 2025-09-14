#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada para Belgrano Tickets
"""

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuración base"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'belgrano_tickets_secret_2025')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tickets.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API de Belgrano Ahorro
    BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')
    BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY')
    
    # Configuración de red
    API_TIMEOUT_SECS = int(os.environ.get('BELGRANO_AHORRO_TIMEOUT', '30'))
    
    # Puerto
    PORT = int(os.environ.get('PORT', '5000'))
    
    @classmethod
    def validate_config(cls):
        """Validar configuración crítica"""
        issues = []
        
        # En producción, estas variables son obligatorias
        if cls.FLASK_ENV == 'production':
            if not cls.BELGRANO_AHORRO_URL:
                issues.append("BELGRANO_AHORRO_URL no configurada en producción")
            
            if not cls.BELGRANO_AHORRO_API_KEY:
                issues.append("BELGRANO_AHORRO_API_KEY no configurada en producción")
        
        return issues
    
    @classmethod
    def log_config_status(cls):
        """Mostrar estado de la configuración"""
        logger.info("🔧 Configuración de la aplicación:")
        logger.info(f"   Entorno: {cls.FLASK_ENV}")
        logger.info(f"   Puerto: {cls.PORT}")
        logger.info(f"   Base de datos: {'Configurada' if cls.SQLALCHEMY_DATABASE_URI else 'No configurada'}")
        logger.info(f"   Belgrano Ahorro URL: {'Configurada' if cls.BELGRANO_AHORRO_URL else 'No configurada'}")
        logger.info(f"   API Key: {'Configurada' if cls.BELGRANO_AHORRO_API_KEY else 'No configurada'}")
        
        # Validar y mostrar issues
        issues = cls.validate_config()
        if issues:
            logger.warning("⚠️ Problemas de configuración encontrados:")
            for issue in issues:
                logger.warning(f"   - {issue}")
        else:
            logger.info("✅ Configuración validada correctamente")

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    FLASK_ENV = 'production'

# Configuración por defecto basada en el entorno
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Obtener configuración basada en el entorno"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
