#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente HTTP para consumir la API de Belgrano Ahorro
"""

import requests
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class BelgranoAhorroAPIClient:
    """Cliente para comunicarse con la API de Belgrano Ahorro"""
    
    def __init__(self, base_url, api_key):
        """
        Inicializar cliente API
        
        Args:
            base_url (str): URL base de la API de Belgrano Ahorro
            api_key (str): Clave de API para autenticación
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-API-Key': api_key
        })
        
        logger.info(f"Cliente API inicializado para: {self.base_url}")
    
    def _make_request(self, method, endpoint, **kwargs):
        """
        Realizar petición HTTP
        
        Args:
            method (str): Método HTTP (GET, POST, PUT, DELETE)
            endpoint (str): Endpoint de la API
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            dict: Respuesta de la API o None si hay error
        """
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {"success": True}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición {method} {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
            return None
    
    def get_productos(self):
        """Obtener lista de productos"""
        return self._make_request('GET', 'productos')
    
    def get_producto(self, producto_id):
        """Obtener producto específico"""
        return self._make_request('GET', f'productos/{producto_id}')
    
    def create_ticket(self, ticket_data):
        """Crear nuevo ticket"""
        return self._make_request('POST', 'tickets', json=ticket_data)
    
    def update_ticket(self, ticket_id, ticket_data):
        """Actualizar ticket existente"""
        return self._make_request('PUT', f'tickets/{ticket_id}', json=ticket_data)
    
    def get_tickets(self):
        """Obtener lista de tickets"""
        return self._make_request('GET', 'tickets')
    
    def get_ticket(self, ticket_id):
        """Obtener ticket específico"""
        return self._make_request('GET', f'tickets/{ticket_id}')
    
    def sync_data(self, data_type, data):
        """Sincronizar datos con Belgrano Ahorro"""
        return self._make_request('POST', f'sync/{data_type}', json=data)
    
    def test_connection(self):
        """Probar conexión con la API"""
        try:
            response = self._make_request('GET', 'health')
            if response:
                logger.info("Conexión con API exitosa")
                return True
            else:
                logger.warning("API no responde correctamente")
                return False
        except Exception as e:
            logger.error(f"Error probando conexión: {e}")
            return False

def create_api_client(base_url=None, api_key=None):
    """
    Crear instancia del cliente API
    
    Args:
        base_url (str): URL base de la API
        api_key (str): Clave de API
    
    Returns:
        BelgranoAhorroAPIClient: Instancia del cliente API
    """
    # Usar variables de entorno si no se proporcionan parámetros
    if not base_url:
        base_url = os.environ.get('BELGRANO_AHORRO_URL')
    if not api_key:
        api_key = os.environ.get('BELGRANO_AHORRO_API_KEY')
    
    if not base_url or not api_key:
        logger.warning("URL base o API key no proporcionados")
        return None
    
    return BelgranoAhorroAPIClient(base_url, api_key)

def test_api_connection(base_url=None, api_key=None):
    """
    Probar conexión con la API
    
    Args:
        base_url (str): URL base de la API
        api_key (str): Clave de API
        
    Returns:
        bool: True si la conexión es exitosa
    """
    client = create_api_client(base_url, api_key)
    if client:
        return client.test_connection()
    return False

# Configuración por defecto usando variables de entorno
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'https://belgranoahorro-hp30.onrender.com')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')

# Detectar entorno
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production'

# Validar variables de entorno críticas
if not BELGRANO_AHORRO_URL or BELGRANO_AHORRO_URL == 'https://belgranoahorro-hp30.onrender.com':
    if not IS_PRODUCTION:
        logger.info("ℹ️ BELGRANO_AHORRO_URL no configurada (normal en desarrollo)")
    else:
        logger.warning("⚠️ Variable de entorno BELGRANO_AHORRO_URL no está definida")

if not BELGRANO_AHORRO_API_KEY or BELGRANO_AHORRO_API_KEY == 'belgrano_ahorro_api_key_2025':
    if not IS_PRODUCTION:
        logger.info("ℹ️ BELGRANO_AHORRO_API_KEY no configurada (normal en desarrollo)")
    else:
        logger.warning("⚠️ Variable de entorno BELGRANO_AHORRO_API_KEY no está definida")

# Cliente global (se inicializa si las variables están disponibles)
api_client = None
if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
    try:
        api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        logger.info("Cliente API global inicializado correctamente")
    except Exception as e:
        logger.warning(f"Error inicializando cliente API: {e}")
        api_client = None
else:
    if IS_PRODUCTION:
        logger.warning("Variables de entorno no configuradas para cliente API global")
    else:
        logger.info("Cliente API no inicializado (variables de entorno no configuradas)")

