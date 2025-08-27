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
    """Cliente para consumir la API de Belgrano Ahorro"""
    
    def __init__(self, base_url, api_key):
        if not base_url or not api_key:
            raise ValueError("base_url y api_key son requeridos")
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = 30
        self.session = requests.Session()
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'User-Agent': 'BelgranoTickets/1.0.0'
        })
        
        logger.info(f"Cliente API inicializado para: {self.base_url}")
    
    def _make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/api/v1{endpoint}"
        
        try:
            logger.debug(f"Realizando {method} a {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {'status': 'success'}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout en petición a {url}")
            raise Exception(f"Timeout en petición a {endpoint}")
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión a {url}")
            raise Exception(f"No se puede conectar a {self.base_url}")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
            try:
                error_data = e.response.json()
                raise Exception(error_data.get('error', f'Error HTTP {e.response.status_code}'))
            except:
                raise Exception(f'Error HTTP {e.response.status_code}')
                
        except Exception as e:
            logger.error(f"Error inesperado en petición a {url}: {e}")
            raise
    
    def health_check(self):
        """Verificar estado de la API de Belgrano Ahorro"""
        try:
            return self._make_request('GET', '/health')
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_productos(self, categoria=None):
        """Obtener productos de Belgrano Ahorro"""
        try:
            if categoria:
                return self._make_request('GET', f'/productos/categoria/{categoria}')
            else:
                return self._make_request('GET', '/productos')
        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}")
            return []
    
    def get_pedido(self, numero_pedido):
        """Obtener un pedido específico"""
        try:
            response = self._make_request('GET', f'/pedidos/{numero_pedido}')
            return response.get('pedido')
        except Exception as e:
            logger.error(f"Error obteniendo pedido {numero_pedido}: {e}")
            return None
    
    def actualizar_estado_pedido(self, numero_pedido, nuevo_estado):
        """Actualizar estado de un pedido en Belgrano Ahorro"""
        try:
            data = {'estado': nuevo_estado}
            response = self._make_request('PUT', f'/pedidos/{numero_pedido}/estado', data=data)
            logger.info(f"Estado del pedido {numero_pedido} actualizado a {nuevo_estado}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando estado del pedido {numero_pedido}: {e}")
            return False
    
    def sync_tickets_to_ahorro(self, tickets):
        """Sincronizar tickets hacia Belgrano Ahorro"""
        try:
            data = {'tickets': tickets}
            response = self._make_request('POST', '/sync/tickets', data=data)
            logger.info(f"{len(tickets)} tickets sincronizados hacia Belgrano Ahorro")
            return True
        except Exception as e:
            logger.error(f"Error sincronizando tickets: {e}")
            return False

def create_api_client(url=None, api_key=None):
    """Crear instancia del cliente API"""
    if url is None or api_key is None:
        raise ValueError("url y api_key son requeridos para crear el cliente API")
    return BelgranoAhorroAPIClient(url, api_key)

def test_api_connection(url=None, api_key=None):
    """Probar conexión con la API de Belgrano Ahorro"""
    try:
        if url is None or api_key is None:
            raise ValueError("url y api_key son requeridos para probar la conexión")
        client = BelgranoAhorroAPIClient(url, api_key)
        health = client.health_check()
        
        if health.get('status') == 'healthy':
            logger.info("✅ Conexión con API de Belgrano Ahorro exitosa")
            return {
                'status': 'success',
                'message': 'Conexión exitosa',
                'health': health
            }
        else:
            logger.warning("⚠️ API de Belgrano Ahorro no está saludable")
            return {
                'status': 'warning',
                'message': 'API no está saludable',
                'health': health
            }
            
    except Exception as e:
        logger.error(f"❌ Error conectando con API de Belgrano Ahorro: {e}")
        return {
            'status': 'error',
            'message': f'Error de conexión: {e}',
            'error': str(e)
        }
