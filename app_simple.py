#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicación Flask simplificada para Belgrano Tickets
Sistema de gestión de tickets y repartidores
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Inicialización Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'

# Configuración de base de datos
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
print(f"🗄️ Ruta de base de datos: {db_path}")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importar modelos
from models import db, User, Ticket, Configuracion

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def inicializar_base_datos():
    """Inicializar base de datos y usuarios por defecto"""
    try:
        print("🔧 Inicializando base de datos...")
        db.create_all()
        print("✅ Base de datos creada/verificada")
        
        # Verificar si ya existen usuarios
        total_usuarios = User.query.count()
        print(f"📊 Usuarios existentes en BD: {total_usuarios}")
        
        if total_usuarios == 0:
            print("🔧 Creando usuarios por defecto...")
            
            # Crear usuario admin
            admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                role='admin',
                nombre='Administrador Principal',
                activo=True,
                fecha_creacion=datetime.utcnow()
            )
            db.session.add(admin)
            print("✅ Usuario admin creado")
            
            # Crear usuarios de flota
            flota_usuarios = [
                {
                    'username': 'repartidor1',
                    'email': 'repartidor1@belgranoahorro.com',
                    'nombre': 'Repartidor 1',
                    'password': 'flota123'
                },
                {
                    'username': 'repartidor2',
                    'email': 'repartidor2@belgranoahorro.com',
                    'nombre': 'Repartidor 2',
                    'password': 'flota123'
                },
                {
                    'username': 'repartidor3',
                    'email': 'repartidor3@belgranoahorro.com',
                    'nombre': 'Repartidor 3',
                    'password': 'flota123'
                },
                {
                    'username': 'repartidor4',
                    'email': 'repartidor4@belgranoahorro.com',
                    'nombre': 'Repartidor 4',
                    'password': 'flota123'
                },
                {
                    'username': 'repartidor5',
                    'email': 'repartidor5@belgranoahorro.com',
                    'nombre': 'Repartidor 5',
                    'password': 'flota123'
                }
            ]
            
            for flota_data in flota_usuarios:
                flota = User(
                    username=flota_data['username'],
                    email=flota_data['email'],
                    password=generate_password_hash(flota_data['password']),
                    role='flota',
                    nombre=flota_data['nombre'],
                    activo=True,
                    fecha_creacion=datetime.utcnow()
                )
                db.session.add(flota)
                print(f"✅ Usuario {flota_data['nombre']} creado")
            
            # Crear configuraciones por defecto
            configuraciones = [
                {
                    'clave': 'sistema_nombre',
                    'valor': 'Belgrano Tickets',
                    'descripcion': 'Nombre del sistema'
                },
                {
                    'clave': 'version',
                    'valor': '2.0.0',
                    'descripcion': 'Versión del sistema'
                }
            ]
            
            for config_data in configuraciones:
                config = Configuracion(
                    clave=config_data['clave'],
                    valor=config_data['valor'],
                    descripcion=config_data['descripcion'],
                    fecha_actualizacion=datetime.utcnow()
                )
                db.session.add(config)
            
            # Commit de todos los cambios
            db.session.commit()
            print("🎉 Inicialización completada exitosamente")
            
            # Verificar usuarios finales
            usuarios_finales = User.query.all()
            print(f"📋 Usuarios en BD después de inicialización:")
            for usuario in usuarios_finales:
                print(f"   - {usuario.email} (Role: {usuario.role})")
            
            # Verificar que las contraseñas funcionan
            print("🔐 Verificando contraseñas...")
            admin_test = User.query.filter_by(email='admin@belgranoahorro.com').first()
            if admin_test and check_password_hash(admin_test.password, 'admin123'):
                print("✅ Contraseña admin verificada correctamente")
            else:
                print("❌ ERROR: Contraseña admin no funciona")
            
            flota_test = User.query.filter_by(email='repartidor1@belgranoahorro.com').first()
            if flota_test and check_password_hash(flota_test.password, 'flota123'):
                print("✅ Contraseña flota verificada correctamente")
            else:
                print("❌ ERROR: Contraseña flota no funciona")
        
        else:
            print("✅ Usuarios ya existen")
        
    except Exception as e:
        print(f"❌ Error en inicialización: {e}")
        db.session.rollback()
        raise e

# Inicializar base de datos al arrancar
with app.app_context():
    inicializar_base_datos()

# Filtro personalizado para JSON
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorador para roles
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Middleware para verificar usuarios en cada request
@app.before_request
def verificar_usuarios():
    """Verificar que existan usuarios en cada request"""
    try:
        # Solo verificar en rutas que no sean de debug
        if not request.path.startswith('/debug') and not request.path.startswith('/health') and not request.path.startswith('/crear_'):
            total_usuarios = User.query.count()
            if total_usuarios == 0:
                print("🚨 No hay usuarios en BD - Inicializando...")
                inicializar_base_datos()
    except Exception as e:
        print(f"❌ Error verificando usuarios: {e}")

# Rutas principales
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('panel'))
    return redirect(url_for('login'))

@app.route('/health')
def health_check():
    """Health check para Render"""
    try:
        # Verificar que la base de datos esté funcionando
        user_count = User.query.count()
        usuarios = User.query.all()
        usuarios_info = []
        for user in usuarios:
            usuarios_info.append({
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'nombre': user.nombre
            })
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'users_count': user_count,
            'users': usuarios_info,
            'message': 'Ticketera funcionando correctamente'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/debug')
def debug_info():
    """Información de debug para verificar estado"""
    try:
        usuarios = User.query.all()
        tickets = Ticket.query.all()
        configs = Configuracion.query.all()
        
        return jsonify({
            'total_usuarios': len(usuarios),
            'total_tickets': len(tickets),
            'total_configs': len(configs),
            'usuarios': [
                {
                    'id': u.id,
                    'email': u.email,
                    'role': u.role,
                    'nombre': u.nombre,
                    'username': u.username,
                    'activo': u.activo
                } for u in usuarios
            ],
            'tickets': [
                {
                    'id': t.id,
                    'numero': t.numero,
                    'estado': t.estado,
                    'cliente_nombre': t.cliente_nombre
                } for t in tickets
            ],
            'credenciales_admin': 'admin@belgranoahorro.com / admin123',
            'credenciales_flota': 'repartidor1@belgranoahorro.com / flota123'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reinicializar')
def reinicializar_usuarios():
    """Forzar reinicialización de usuarios"""
    try:
        # Eliminar todos los usuarios existentes
        User.query.delete()
        db.session.commit()
        print("🗑️ Usuarios eliminados")
        
        # Ejecutar inicialización
        inicializar_base_datos()
        
        return jsonify({
            'status': 'success',
            'message': 'Usuarios reinicializados correctamente',
            'credenciales_admin': 'admin@belgranoahorro.com / admin123',
            'credenciales_flota': 'repartidor1@belgranoahorro.com / flota123'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/crear_admin_emergencia')
def crear_admin_emergencia():
    """Crear admin de emergencia"""
    try:
        # Verificar si admin existe
        admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
        if admin:
            # Actualizar contraseña
            admin.password = generate_password_hash('admin123')
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Admin actualizado',
                'email': 'admin@belgranoahorro.com',
                'password': 'admin123'
            }), 200
        else:
            # Crear admin nuevo
            admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                role='admin',
                nombre='Administrador Principal',
                activo=True,
                fecha_creacion=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Admin creado de emergencia',
                'email': 'admin@belgranoahorro.com',
                'password': 'admin123'
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/crear_flota_emergencia')
def crear_flota_emergencia():
    """Crear flota de emergencia"""
    try:
        # Crear repartidor 1
        flota = User.query.filter_by(email='repartidor1@belgranoahorro.com').first()
        if flota:
            # Actualizar contraseña
            flota.password = generate_password_hash('flota123')
            db.session.commit()
        else:
            # Crear flota nuevo
            flota = User(
                username='repartidor1',
                email='repartidor1@belgranoahorro.com',
                password=generate_password_hash('flota123'),
                role='flota',
                nombre='Repartidor 1',
                activo=True,
                fecha_creacion=datetime.utcnow()
            )
            db.session.add(flota)
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Flota creada/actualizada de emergencia',
            'email': 'repartidor1@belgranoahorro.com',
            'password': 'flota123'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/crear_usuarios_directo')
def crear_usuarios_directo():
    """Crear usuarios directamente sin verificar"""
    try:
        # Eliminar todos los usuarios
        User.query.delete()
        db.session.commit()
        
        # Crear admin
        admin = User(
            username='admin',
            email='admin@belgranoahorro.com',
            password=generate_password_hash('admin123'),
            role='admin',
            nombre='Administrador Principal',
            activo=True,
            fecha_creacion=datetime.utcnow()
        )
        db.session.add(admin)
        
        # Crear flota
        flota = User(
            username='repartidor1',
            email='repartidor1@belgranoahorro.com',
            password=generate_password_hash('flota123'),
            role='flota',
            nombre='Repartidor 1',
            activo=True,
            fecha_creacion=datetime.utcnow()
        )
        db.session.add(flota)
        
        db.session.commit()
        
        # Verificar
        usuarios = User.query.all()
        
        return jsonify({
            'status': 'success',
            'message': 'Usuarios creados directamente',
            'usuarios_creados': len(usuarios),
            'admin': {
                'email': 'admin@belgranoahorro.com',
                'password': 'admin123',
                'role': 'admin'
            },
            'flota': {
                'email': 'repartidor1@belgranoahorro.com',
                'password': 'flota123',
                'role': 'flota'
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"🔐 Intento de login: {email}")
        
        # Debug: mostrar todos los usuarios en la base de datos
        todos_usuarios = User.query.all()
        print(f"📊 Total de usuarios en BD: {len(todos_usuarios)}")
        for u in todos_usuarios:
            print(f"   - {u.email} (Role: {u.role})")
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"✅ Usuario encontrado: {user.nombre} (ID: {user.id})")
            print(f"   Role: {user.role}")
            print(f"   Activo: {user.activo}")
            
            if not user.activo:
                print("❌ Usuario inactivo")
                flash('Usuario inactivo', 'danger')
                return render_template('login.html')
            
            if check_password_hash(user.password, password):
                print("✅ Contraseña correcta - Login exitoso")
                login_user(user)
                return redirect(url_for('panel'))
            else:
                print("❌ Contraseña incorrecta")
                flash('Contraseña incorrecta', 'danger')
        else:
            print(f"❌ Usuario no encontrado: {email}")
            flash('Usuario no encontrado', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/panel')
@login_required
def panel():
    if current_user.role == 'admin':
        # Ordenar tickets por fecha de creación (más reciente primero)
        tickets = Ticket.query.order_by(Ticket.fecha_creacion.desc()).all()
        return render_template('admin_panel.html', tickets=tickets)
    elif current_user.role == 'flota':
        tickets = Ticket.query.filter_by(asignado_a=current_user.id).order_by(Ticket.fecha_creacion.desc()).all()
        return render_template('flota_panel.html', tickets=tickets)
    else:
        return 'Acceso no permitido', 403

@app.route('/ticket/<int:ticket_id>')
@login_required
def detalle_ticket(ticket_id):
    """Ver detalles de un ticket específico"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verificar permisos
    if current_user.role == 'flota' and ticket.asignado_a != current_user.id:
        abort(403)
    
    return render_template('detalle_ticket.html', ticket=ticket)

@app.route('/ticket/<int:ticket_id>/cambiar_estado', methods=['POST'])
@login_required
def cambiar_estado_ticket(ticket_id):
    """Cambiar estado de un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verificar permisos
    if current_user.role == 'flota' and ticket.asignado_a != current_user.id:
        abort(403)
    
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ['pendiente', 'en_proceso', 'entregado', 'cancelado']:
        ticket.estado = nuevo_estado
        
        if nuevo_estado == 'entregado':
            ticket.fecha_entrega = datetime.utcnow()
        
        db.session.commit()
        flash(f'Estado del ticket cambiado a {nuevo_estado}', 'success')
    
    return redirect(url_for('detalle_ticket', ticket_id=ticket_id))

@app.route('/ticket/<int:ticket_id>/asignar', methods=['POST'])
@login_required
@role_required('admin')
def asignar_ticket(ticket_id):
    """Asignar ticket a un repartidor"""
    ticket = Ticket.query.get_or_404(ticket_id)
    repartidor_id = request.form.get('repartidor_id')
    
    if repartidor_id:
        repartidor = User.query.filter_by(id=repartidor_id, role='flota').first()
        if repartidor:
            ticket.asignado_a = repartidor.id
            ticket.repartidor_nombre = repartidor.nombre
            ticket.fecha_asignacion = datetime.utcnow()
            db.session.commit()
            flash(f'Ticket asignado a {repartidor.nombre}', 'success')
    
    return redirect(url_for('detalle_ticket', ticket_id=ticket_id))

@app.route('/ticket/<int:ticket_id>/agregar_nota', methods=['POST'])
@login_required
def agregar_nota_ticket(ticket_id):
    """Agregar nota a un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verificar permisos
    if current_user.role == 'flota' and ticket.asignado_a != current_user.id:
        abort(403)
    
    nota = request.form.get('nota')
    if nota:
        if ticket.notas_repartidor:
            ticket.notas_repartidor += f"\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}: {nota}"
        else:
            ticket.notas_repartidor = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}: {nota}"
        
        db.session.commit()
        flash('Nota agregada correctamente', 'success')
    
    return redirect(url_for('detalle_ticket', ticket_id=ticket_id))

# Rutas de gestión (solo admin)
@app.route('/gestion_usuarios')
@login_required
@role_required('admin')
def gestion_usuarios():
    usuarios = User.query.all()
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@app.route('/gestion_flota')
@login_required
@role_required('admin')
def gestion_flota():
    repartidores = User.query.filter_by(role='flota').all()
    tickets = Ticket.query.all()
    return render_template('gestion_flota.html', repartidores=repartidores, tickets=tickets)

@app.route('/reportes')
@login_required
@role_required('admin')
def reportes():
    total_tickets = Ticket.query.count()
    tickets_pendientes = Ticket.query.filter_by(estado='pendiente').count()
    tickets_en_proceso = Ticket.query.filter_by(estado='en_proceso').count()
    tickets_entregados = Ticket.query.filter_by(estado='entregado').count()
    
    return render_template('reportes.html', 
                         total_tickets=total_tickets,
                         tickets_pendientes=tickets_pendientes,
                         tickets_en_proceso=tickets_en_proceso,
                         tickets_entregados=tickets_entregados)

if __name__ == "__main__":
    print("🚀 Iniciando aplicación de tickets simplificada en puerto 5001...")
    print("🔐 Credenciales disponibles:")
    print("   • Admin: admin@belgranoahorro.com / admin123")
    print("   • Flota: repartidor1@belgranoahorro.com / flota123")
    app.run(debug=True, host='0.0.0.0', port=5001)
