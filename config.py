#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada para Belgrano Tickets
"""

import os
import logging

logger = logging.getLogger(__name__)

# Valores por defecto solo para desarrollo (en producción deben venir por entorno)
BELGRANO_AHORRO_API_KEY = os.getenv("BELGRANO_AHORRO_API_KEY") or ("dev_key_placeholder" if os.getenv('FLASK_ENV','development')!='production' else None)
DEVOPS_API_KEY = os.getenv("DEVOPS_API_KEY") or ("devops_key_placeholder" if os.getenv('FLASK_ENV','development')!='production' else None)

BELGRANO_AHORRO_URL = os.getenv("BELGRANO_AHORRO_URL") or ("https://belgranoahorro-hp30.onrender.com" if os.getenv('FLASK_ENV','development')!='production' else None)
DEVOPS_API_URL = os.getenv("DEVOPS_API_URL") or os.getenv("TICKETERA_URL") or ("http://localhost:5002" if os.getenv('FLASK_ENV','development')!='production' else None)


def load_env_defaults() -> None:
    """Asegura que existan variables mínimas con valores por defecto y emite warnings.

    No levanta excepciones: la app debe poder iniciar en entornos de dev/test sin bloquearse.
    """
    defaults = {
        "BELGRANO_AHORRO_API_KEY": BELGRANO_AHORRO_API_KEY,
        "DEVOPS_API_KEY": DEVOPS_API_KEY,
        "BELGRANO_AHORRO_URL": BELGRANO_AHORRO_URL,
        "DEVOPS_API_URL": DEVOPS_API_URL,
    }

    for key, value in defaults.items():
        if value is None:
            # En producción no seteamos defaults
            continue
        if not os.getenv(key):
            os.environ[key] = value
            logger.warning(f"ENV {key} no configurada, usando valor por defecto: {value}")


def validate_env_non_blocking() -> None:
    """Valida variables críticas y emite warnings si faltan o parecen inválidas."""
    checks = [
        ("BELGRANO_AHORRO_URL", os.getenv("BELGRANO_AHORRO_URL")),
        ("BELGRANO_AHORRO_API_KEY", os.getenv("BELGRANO_AHORRO_API_KEY")),
        ("DEVOPS_API_URL", os.getenv("DEVOPS_API_URL")),
        ("DEVOPS_API_KEY", os.getenv("DEVOPS_API_KEY")),
    ]

    for name, val in checks:
        if not val or str(val).strip() == "":
            logger.warning(f"ENV {name} ausente; ciertas funciones externas podrían fallar")


class Config:
    """Configuración base"""
    
    # Flask
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    # Evitar secretos hardcodeados: en dev generamos uno aleatorio si no existe; en prod exigimos SECRET_KEY
    SECRET_KEY = os.environ.get('SECRET_KEY') or (os.urandom(32).hex() if FLASK_ENV != 'production' else None)
    
    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tickets.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API de Belgrano Ahorro
    BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')
    BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY')
    
    # Ticketera: soportar nombres nuevos y legados de variables de entorno
    TICKETS_API_URL = (
        os.environ.get('TICKETS_API_URL')
        or os.environ.get('TICKETERA_URL')
        or os.environ.get('TICKETING_URL')
    )
    TICKETS_API_KEY = (
        os.environ.get('TICKETS_API_KEY')
        or os.environ.get('TICKETERA_API_KEY')
        or os.environ.get('TICKETING_API_KEY')
    )
    TICKETS_API_USERNAME = (
        os.environ.get('TICKETS_API_USERNAME')
        or os.environ.get('TICKETERA_USER')
        or os.environ.get('TICKETING_USER')
    )
    TICKETS_API_PASSWORD = (
        os.environ.get('TICKETS_API_PASSWORD')
        or os.environ.get('TICKETERA_PASSWORD')
        or os.environ.get('TICKETING_PASSWORD')
    )
    
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
            if not cls.SECRET_KEY:
                issues.append("SECRET_KEY no configurada en producción")
            if not cls.SQLALCHEMY_DATABASE_URI or cls.SQLALCHEMY_DATABASE_URI.startswith('sqlite:'):
                issues.append("DATABASE_URL inválida o usando sqlite en producción")
            if not cls.BELGRANO_AHORRO_URL:
                issues.append("BELGRANO_AHORRO_URL no configurada en producción")
            if not cls.BELGRANO_AHORRO_API_KEY:
                issues.append("BELGRANO_AHORRO_API_KEY no configurada en producción")
            # Ticketera: requerir URL y método de autenticación (API Key o user/pass)
            if not cls.TICKETS_API_URL:
                issues.append("TICKETS_API_URL/TICKETERA_URL no configurada en producción")
            if not (cls.TICKETS_API_KEY or (cls.TICKETS_API_USERNAME and cls.TICKETS_API_PASSWORD)):
                issues.append("Credenciales de ticketera no configuradas (API Key o usuario/contraseña)")
        
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
        logger.info(f"   Ticketera URL: {'Configurada' if cls.TICKETS_API_URL else 'No configurada'}")
        logger.info(f"   Ticketera auth: {'API Key' if cls.TICKETS_API_KEY else ('Usuario/Password' if (cls.TICKETS_API_USERNAME and cls.TICKETS_API_PASSWORD) else 'No configurada')}")
        
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
