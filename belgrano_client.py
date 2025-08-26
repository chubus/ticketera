#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente API para conectar Belgrano Tickets con Belgrano Ahorro
"""

import requests
import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class BelgranoAhorroClient:
    """Cliente para conectar con la API de Belgrano Ahorro"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        Inicializar cliente
        
        Args:
            base_url: URL base de Belgrano Ahorro
            timeout: Timeout para requests en segundos
        """
        self.base_url = base_url or os.environ.get('BELGRANO_AHORRO_URL', 'http://localhost:5000')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configurar headers por defecto
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BelgranoTickets/1.0'
        })
        
        logger.info(f"🔗 Cliente inicializado para: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Realizar request a la API
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Respuesta JSON o None si hay error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en request a {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Probar conexión con Belgrano Ahorro
        
        Returns:
            True si la conexión es exitosa
        """
        logger.info("🔍 Probando conexión con Belgrano Ahorro...")
        
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Conexión exitosa con Belgrano Ahorro")
                return True
            else:
                logger.warning(f"⚠️ Respuesta inesperada: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def get_usuarios(self) -> List[Dict]:
        """
        Obtener lista de usuarios desde Belgrano Ahorro
        
        Returns:
            Lista de usuarios
        """
        logger.info("👥 Obteniendo usuarios desde Belgrano Ahorro...")
        
        response = self._make_request('GET', '/api/tickets/usuarios')
        if response:
            logger.info(f"✅ Obtenidos {len(response)} usuarios")
            return response
        else:
            logger.warning("⚠️ No se pudieron obtener usuarios")
            return []
    
    def get_productos(self) -> List[Dict]:
        """
        Obtener lista de productos desde Belgrano Ahorro
        
        Returns:
            Lista de productos
        """
        logger.info("📦 Obteniendo productos desde Belgrano Ahorro...")
        
        response = self._make_request('GET', '/api/tickets/productos')
        if response:
            logger.info(f"✅ Obtenidos {len(response)} productos")
            return response
        else:
            logger.warning("⚠️ No se pudieron obtener productos")
            return []
    
    def verificar_usuario(self, email: str, password: str) -> Optional[Dict]:
        """
        Verificar credenciales de usuario
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            Datos del usuario si las credenciales son válidas
        """
        logger.info(f"🔐 Verificando usuario: {email}")
        
        data = {
            'email': email,
            'password': password
        }
        
        response = self._make_request('POST', '/api/tickets/verificar_usuario', json=data)
        if response:
            logger.info("✅ Usuario verificado exitosamente")
            return response
        else:
            logger.warning("⚠️ Error al verificar usuario")
            return None
    
    def get_negocios(self) -> List[Dict]:
        """
        Obtener lista de negocios desde Belgrano Ahorro
        
        Returns:
            Lista de negocios
        """
        logger.info("🏪 Obteniendo negocios desde Belgrano Ahorro...")
        
        response = self._make_request('GET', '/api/tickets/negocios')
        if response:
            logger.info(f"✅ Obtenidos {len(response)} negocios")
            return response
        else:
            logger.warning("⚠️ No se pudieron obtener negocios")
            return []
    
    def get_sucursales(self, negocio_id: str) -> List[Dict]:
        """
        Obtener sucursales de un negocio específico
        
        Args:
            negocio_id: ID del negocio
            
        Returns:
            Lista de sucursales
        """
        logger.info(f"🏪 Obteniendo sucursales del negocio: {negocio_id}")
        
        response = self._make_request('GET', f'/api/tickets/negocios/{negocio_id}/sucursales')
        if response:
            logger.info(f"✅ Obtenidas {len(response)} sucursales")
            return response
        else:
            logger.warning("⚠️ No se pudieron obtener sucursales")
            return []
    
    def get_productos_sucursal(self, negocio_id: str, sucursal_id: str) -> List[Dict]:
        """
        Obtener productos de una sucursal específica
        
        Args:
            negocio_id: ID del negocio
            sucursal_id: ID de la sucursal
            
        Returns:
            Lista de productos
        """
        logger.info(f"📦 Obteniendo productos de sucursal: {sucursal_id}")
        
        response = self._make_request('GET', f'/api/tickets/negocios/{negocio_id}/sucursales/{sucursal_id}/productos')
        if response:
            logger.info(f"✅ Obtenidos {len(response)} productos de la sucursal")
            return response
        else:
            logger.warning("⚠️ No se pudieron obtener productos de la sucursal")
            return []

# Instancia global del cliente
belgrano_client = BelgranoAhorroClient()

def test_conexion_completa():
    """Función de prueba para verificar la conexión completa"""
    print("🧪 Probando conexión completa con Belgrano Ahorro...")
    
    # Probar conexión básica
    if not belgrano_client.test_connection():
        print("❌ No se pudo conectar con Belgrano Ahorro")
        return False
    
    # Probar obtener productos
    productos = belgrano_client.get_productos()
    if productos:
        print(f"✅ Conexión exitosa - {len(productos)} productos disponibles")
        return True
    else:
        print("⚠️ Conexión básica OK, pero no se pudieron obtener productos")
        return False

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Probar conexión
    test_conexion_completa()
