import os
import json
import requests
from functools import wraps
from datetime import datetime
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint para DevOps
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Configuración de comunicación con Belgrano Ahorro
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'http://localhost:5000')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')  

# Credenciales DevOps (en producción deberían estar en variables de entorno)
DEVOPS_USERNAME = os.environ.get('DEVOPS_USERNAME', 'devops')
DEVOPS_PASSWORD = os.environ.get('DEVOPS_PASSWORD', 'devops2025')

def devops_required(f):
    """Decorador para verificar acceso DevOps"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('devops_authenticated'):
            return redirect(url_for('devops.login'))
        return f(*args, **kwargs)
    return decorated_function

@devops_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login específico para DevOps"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == DEVOPS_USERNAME and password == DEVOPS_PASSWORD:
            session['devops_authenticated'] = True
            session['devops_username'] = username
            flash('Acceso DevOps autorizado', 'success')
            return redirect(url_for('devops.dashboard'))
        else:
            flash('Credenciales DevOps incorrectas', 'error')

    return render_template('devops/login.html')

@devops_bp.route('/logout')
def logout():
    """Logout de DevOps"""
    session.pop('devops_authenticated', None)
    session.pop('devops_username', None)
    flash('Sesión DevOps cerrada', 'info')
    return redirect(url_for('devops.login'))

@devops_bp.route('/dashboard')
@devops_required
def dashboard():
    """Dashboard principal de DevOps"""
    try:
        # Obtener estadísticas básicas
        stats = {
            'productos_count': len(get_productos_from_belgrano()),
            'sucursales_count': len(get_sucursales_from_belgrano()),
            'ofertas_count': len(get_ofertas_from_belgrano()),
            'precios_count': len(get_precios_from_belgrano())
        }
        return render_template('devops/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error en dashboard DevOps: {e}")
        flash('Error cargando dashboard', 'error')
        return render_template('devops/dashboard.html', stats={})

@devops_bp.route('/productos')
@devops_required
def productos():
    """Gestión de productos"""
    try:
        productos = get_productos_from_belgrano()
        return render_template('devops/productos.html', productos=productos)
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        flash('Error cargando productos', 'error')
        return render_template('devops/productos.html', productos=[])

@devops_bp.route('/sucursales')
@devops_required
def sucursales():
    """Gestión de sucursales"""
    try:
        sucursales = get_sucursales_from_belgrano()
        return render_template('devops/sucursales.html', sucursales=sucursales)
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        flash('Error cargando sucursales', 'error')
        return render_template('devops/sucursales.html', sucursales=[])

@devops_bp.route('/ofertas')
@devops_required
def ofertas():
    """Gestión de ofertas"""
    try:
        ofertas = get_ofertas_from_belgrano()
        return render_template('devops/ofertas.html', ofertas=ofertas)
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        flash('Error cargando ofertas', 'error')
        return render_template('devops/ofertas.html', ofertas=[])

@devops_bp.route('/precios')
@devops_required
def precios():
    """Gestión de precios"""
    try:
        precios = get_precios_from_belgrano()
        return render_template('devops/precios.html', precios=precios)
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        flash('Error cargando precios', 'error')
        return render_template('devops/precios.html', precios=[])

@devops_bp.route('/negocios')
@devops_required
def negocios():
    """Gestión de negocios"""
    try:
        negocios = get_negocios_from_belgrano()
        return render_template('devops/negocios.html', negocios=negocios)
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        flash('Error cargando negocios', 'error')
        return render_template('devops/negocios.html', negocios=[])

# Funciones auxiliares para obtener datos de Belgrano Ahorro
def get_productos_from_belgrano():
    """Obtener productos desde Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/productos",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        return []

def get_sucursales_from_belgrano():
    """Obtener sucursales desde Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/sucursales",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        return []

def get_ofertas_from_belgrano():
    """Obtener ofertas desde Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/ofertas",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return []

def get_precios_from_belgrano():
    """Obtener precios desde Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/precios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        return []

def get_negocios_from_belgrano():
    """Obtener negocios desde Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/negocios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        return []
