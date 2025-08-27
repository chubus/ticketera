import os
from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_socketio import SocketIO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialización Flask y extensiones
app = Flask(__name__)
app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'

# Configuración de base de datos - USAR RUTA ABSOLUTA
import os
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importar db desde models
from models import db, User, Ticket

# ==========================================
# CONFIGURACIÓN DE COMUNICACIÓN API
# ==========================================
# Variables de entorno para comunicación entre servicios
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'http://localhost:5000')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')

# URLs de producción (Render.com)
if os.environ.get('RENDER_ENVIRONMENT') == 'production':
    BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'https://belgrano-ahorro.onrender.com')
    BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')

print(f"🔗 Configuración API:")
print(f"   BELGRANO_AHORRO_URL: {BELGRANO_AHORRO_URL}")
print(f"   API_KEY: {BELGRANO_AHORRO_API_KEY[:10]}...")

# ==========================================

# Importar cliente API
try:
    from api_client import create_api_client, test_api_connection
    api_client = create_api_client()
    print("Cliente API de Belgrano Ahorro inicializado")
except ImportError as e:
    print(f"No se pudo inicializar el cliente API: {e}")
    api_client = None

# Inicializar db con la app
db.init_app(app)

# Crear contexto de aplicación para inicializar la base de datos
with app.app_context():
    db.create_all()
    
    # Inicializar usuarios automáticamente si no existen
    def inicializar_usuarios_automaticamente():
        """Inicializar usuarios automáticamente si no existen"""
        try:
            usuarios_existentes = User.query.count()
            if usuarios_existentes == 0:
                print("No hay usuarios en BD - Creando usuarios automáticamente...")
                
                # Usuario Admin
                admin = User(
                    username='admin',
                    email='admin@belgranoahorro.com',
                    password=generate_password_hash('admin123'),
                    role='admin',
                    nombre='Administrador Principal',
                    activo=True
                )
                db.session.add(admin)
                print("Usuario admin creado: admin@belgranoahorro.com / admin123")
                
                # Usuarios Flota
                flota_usuarios = [
                    ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
                    ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
                    ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
                    ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
                    ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
                ]
                
                for username, email, nombre in flota_usuarios:
                    flota = User(
                        username=username,
                        email=email,
                        password=generate_password_hash('flota123'),
                        role='flota',
                        nombre=nombre,
                        activo=True
                    )
                    db.session.add(flota)
                    print(f"Usuario flota creado: {email} / flota123")
                
                db.session.commit()
                print("Usuarios inicializados automáticamente")
                return True
            else:
                print(f"Ya existen {usuarios_existentes} usuarios en la BD")
                return False
        except Exception as e:
            print(f"Error inicializando usuarios: {e}")
            db.session.rollback()
            return False
    
    # Ejecutar inicialización automática
    inicializar_usuarios_automaticamente()
login_manager = LoginManager(app)
socketio = SocketIO(app, async_mode='threading')

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
            if not hasattr(current_user, 'role') or current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Rutas principales
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('panel'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"Intento de login: {email}")
        
        # Validaciones básicas
        if not email or not password:
            flash('Por favor complete todos los campos', 'warning')
            return render_template('login.html')
        
        # Buscar usuario por email
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"Usuario encontrado: {user.nombre} (ID: {user.id})")
            print(f"   Role: {user.role}")
            print(f"   Activo: {user.activo}")
            
            # Verificar si el usuario está activo
            if not user.activo:
                print("Usuario inactivo")
                flash('Usuario inactivo. Contacte al administrador.', 'danger')
                return render_template('login.html')
            
            # Verificar contraseña
            if check_password_hash(user.password, password):
                print("Contraseña correcta - Login exitoso")
                login_user(user)
                flash(f'Bienvenido, {user.nombre}!', 'success')
                return redirect(url_for('panel'))
            else:
                print("Contraseña incorrecta")
                flash('Email o contraseña incorrectos', 'danger')
        else:
            print(f"Usuario no encontrado: {email}")
            flash('Email o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/debug/credenciales')
@login_required
def debug_credenciales():
    """Ruta de debug para verificar credenciales (solo en desarrollo)"""
    # Solo permitir en desarrollo
    if app.config.get('ENV') == 'production':
        logger.warning(f"Intento de acceso a debug en producción desde {request.remote_addr}")
        return jsonify({'error': 'Endpoint no disponible en producción'}), 404
    try:
        usuarios = User.query.all()
        credenciales = []
        
        for user in usuarios:
            credenciales.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'nombre': user.nombre,
                'role': user.role,
                'activo': user.activo,
                'password_hash': user.password[:50] + '...' if user.password else 'None'
            })
        
        return jsonify({
            'status': 'success',
            'total_usuarios': len(usuarios),
            'usuarios': credenciales,
            'credenciales_admin': {
                'email': 'admin@belgranoahorro.com',
                'password': 'admin123'
            },
            'credenciales_flota': {
                'email': 'repartidor1@belgranoahorro.com',
                'password': 'flota123'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check para verificar que la aplicación esté funcionando"""
    try:
        # Verificar que la base de datos esté funcionando
        total_tickets = Ticket.query.count()
        total_usuarios = User.query.count()
        
        # Verificar conexión con API de Belgrano Ahorro
        ahorro_api_status = "unknown"
        if api_client:
            try:
                health = api_client.health_check()
                ahorro_api_status = health.get('status', 'unknown')
            except:
                ahorro_api_status = "disconnected"
        
        return jsonify({
            'status': 'healthy',
            'service': 'Belgrano Tickets',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'ahorro_api': ahorro_api_status,
            'total_tickets': total_tickets,
            'total_usuarios': total_usuarios,
            'version': '2.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/debug/reparar_credenciales', methods=['POST'])
def reparar_credenciales_debug():
    """Ruta para reparar credenciales en producción"""
    try:
        # Verificar si es producción
        if app.config.get('ENV') == 'production':
            # Solo permitir en producción si hay un token secreto
            token = request.headers.get('X-Repair-Token')
            if token != 'belgrano_repair_2025':
                return jsonify({'error': 'Token no válido'}), 403
        
        # Ejecutar reparación
        from werkzeug.security import generate_password_hash
        
        # Buscar o crear usuario admin
        admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
        
        if admin:
            admin.password = generate_password_hash('admin123')
            admin.activo = True
            admin.role = 'admin'
            admin.nombre = 'Administrador Principal'
        else:
            admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                role='admin',
                nombre='Administrador Principal',
                activo=True
            )
            db.session.add(admin)
        
        # Verificar usuarios flota
        flota_emails = [
            'repartidor1@belgranoahorro.com',
            'repartidor2@belgranoahorro.com',
            'repartidor3@belgranoahorro.com',
            'repartidor4@belgranoahorro.com',
            'repartidor5@belgranoahorro.com'
        ]
        
        flota_nombres = [
            'Repartidor 1',
            'Repartidor 2',
            'Repartidor 3',
            'Repartidor 4',
            'Repartidor 5'
        ]
        
        for i, email in enumerate(flota_emails):
            flota_user = User.query.filter_by(email=email).first()
            
            if flota_user:
                flota_user.password = generate_password_hash('flota123')
                flota_user.activo = True
                flota_user.role = 'flota'
                flota_user.nombre = flota_nombres[i]
            else:
                flota_user = User(
                    username=f'repartidor{i+1}',
                    email=email,
                    password=generate_password_hash('flota123'),
                    role='flota',
                    nombre=flota_nombres[i],
                    activo=True
                )
                db.session.add(flota_user)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Credenciales reparadas exitosamente',
            'credenciales': {
                'admin': 'admin@belgranoahorro.com / admin123',
                'flota': 'repartidor1@belgranoahorro.com / flota123'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

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

# Endpoint REST para recibir tickets desde la app principal
@app.route('/api/tickets/recibir', methods=['POST'])
def recibir_ticket_externo():
    """
    Endpoint para recibir tickets desde la aplicación principal de Belgrano Ahorro
    """
    try:
        # Autenticación por API Key
        api_key_header = request.headers.get('X-API-Key')
        if not api_key_header or api_key_header != BELGRANO_AHORRO_API_KEY:
            return jsonify({'error': 'API key inválida'}), 401

        data = request.get_json()
        print(f"Datos recibidos en Ticketera:")
        print(f"   Datos: {json.dumps(data, indent=2)}")
        
        if not data:
            print("No se recibieron datos")
            return jsonify({'error': 'Datos no recibidos'}), 400
        
        # Determinar prioridad basada en tipo de cliente
        prioridad = data.get('prioridad', 'normal')
        tipo_cliente = data.get('tipo_cliente', 'cliente')
        
        # Si es comerciante, asegurar prioridad alta
        if tipo_cliente == 'comerciante' and prioridad != 'alta':
            prioridad = 'alta'
        
        # Idempotencia: si ya existe un ticket con el mismo numero, devolverlo
        numero_ticket = data.get('numero', data.get('numero_pedido'))
        if numero_ticket:
            existente = Ticket.query.filter_by(numero=numero_ticket).first()
            if existente:
                return jsonify({'exito': True, 'ticket_id': existente.id, 'idempotent': True}), 200

        # Crear el ticket con los datos recibidos
        ticket = Ticket(
            numero=numero_ticket or f'TICKET-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            cliente_nombre=data.get('cliente_nombre', data.get('cliente', 'Cliente')),
            cliente_direccion=data.get('cliente_direccion', data.get('direccion', 'Sin dirección')),
            cliente_telefono=data.get('cliente_telefono', data.get('telefono', 'Sin teléfono')),
            cliente_email=data.get('cliente_email', data.get('email', 'sin@email.com')),
            productos=json.dumps(data.get('productos', [])),
            estado=data.get('estado', 'pendiente'),
            prioridad=prioridad,
            indicaciones=data.get('indicaciones', data.get('notas', ''))
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Asignar automáticamente a un repartidor aleatorio
        repartidor_asignado = asignar_repartidor_automatico(ticket)
        if repartidor_asignado:
            ticket.repartidor_nombre = repartidor_asignado
            db.session.commit()
            print(f"Ticket asignado automáticamente a {repartidor_asignado}")
        
        # Emitir evento WebSocket para actualización en tiempo real
        socketio.emit('nuevo_ticket', {
            'ticket_id': ticket.id, 
            'numero': ticket.numero,
            'cliente_nombre': ticket.cliente_nombre,
            'estado': ticket.estado,
            'repartidor': ticket.repartidor_nombre,
            'prioridad': ticket.prioridad,
            'tipo_cliente': tipo_cliente
        })
        
        # Mensaje de log más detallado
        tipo_cliente_str = "COMERCIANTE" if tipo_cliente == 'comerciante' else "CLIENTE"
        print(f"Ticket recibido exitosamente: {ticket.numero} - {ticket.cliente_nombre} ({tipo_cliente_str}) - Prioridad: {ticket.prioridad}")
        return jsonify({'exito': True, 'ticket_id': ticket.id, 'repartidor_asignado': ticket.repartidor_nombre})
        
    except Exception as e:
        print(f"Error al procesar ticket: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def asignar_repartidor_automatico(ticket):
    """
    Asigna automáticamente un repartidor aleatorio que no tenga tickets de prioridad máxima
    """
    import random
    
    # Lista de repartidores disponibles
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    
    # Filtrar repartidores que no tengan tickets de prioridad máxima
    repartidores_disponibles = []
    
    for repartidor in repartidores:
        # Contar tickets de prioridad máxima para este repartidor
        tickets_prioridad_maxima = Ticket.query.filter_by(
            repartidor_nombre=repartidor, 
            prioridad='alta'
        ).count()
        
        # Si no tiene tickets de prioridad máxima, está disponible
        if tickets_prioridad_maxima == 0:
            repartidores_disponibles.append(repartidor)
    
    # Si no hay repartidores disponibles sin prioridad máxima, usar todos
    if not repartidores_disponibles:
        repartidores_disponibles = repartidores
    
    # Seleccionar aleatoriamente
    if repartidores_disponibles:
        return random.choice(repartidores_disponibles)
    
    return None

@app.route('/api/tickets', methods=['POST'])
def recibir_ticket():
    """
    Endpoint alternativo para recibir tickets (mantener compatibilidad)
    """
    return recibir_ticket_externo()

@app.route('/ticket/<int:ticket_id>/estado', methods=['POST'])
@login_required
def actualizar_estado_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    nuevo_estado = request.form.get('estado')
    nueva_prioridad = request.form.get('prioridad')
    nuevas_indicaciones = request.form.get('indicaciones')
    
    if nuevo_estado:
        ticket.estado = nuevo_estado
    if nueva_prioridad:
        ticket.prioridad = nueva_prioridad
    if nuevas_indicaciones is not None:  # Permitir strings vacíos
        ticket.indicaciones = nuevas_indicaciones
    
    db.session.commit()
    
    # Emitir evento WebSocket para actualización en tiempo real
    socketio.emit('ticket_actualizado', {
        'ticket_id': ticket.id,
        'estado': ticket.estado,
        'prioridad': ticket.prioridad
    })
    
    return jsonify({'exito': True, 'mensaje': 'Ticket actualizado correctamente'})



@app.route('/gestion_flota')
@login_required
def gestion_flota():
    if current_user.role != 'admin':
        return 'Acceso no permitido', 403
    
    # Obtener todos los repartidores disponibles
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    
    # Obtener tickets con repartidores asignados
    tickets_asignados = Ticket.query.filter(Ticket.repartidor_nombre.isnot(None)).all()
    
    # Estadísticas por repartidor
    stats_repartidores = {}
    for rep in repartidores:
        tickets_rep = Ticket.query.filter_by(repartidor_nombre=rep).all()
        stats_repartidores[rep] = {
            'total': len(tickets_rep),
            'pendientes': len([t for t in tickets_rep if t.estado == 'pendiente']),
            'en_camino': len([t for t in tickets_rep if t.estado == 'en-camino']),
            'entregados': len([t for t in tickets_rep if t.estado == 'entregado'])
        }
    
    return render_template('gestion_flota.html', 
                         repartidores=repartidores, 
                         tickets_asignados=tickets_asignados,
                         stats_repartidores=stats_repartidores)

@app.route('/reportes')
@login_required
def reportes():
    if current_user.role != 'admin':
        return 'Acceso no permitido', 403
    
    # Estadísticas generales
    total_tickets = Ticket.query.count()
    tickets_pendientes = Ticket.query.filter_by(estado='pendiente').count()
    tickets_en_camino = Ticket.query.filter_by(estado='en-camino').count()
    tickets_entregados = Ticket.query.filter_by(estado='entregado').count()
    
    # Tickets por repartidor
    tickets_por_repartidor = {}
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    for rep in repartidores:
        tickets_por_repartidor[rep] = Ticket.query.filter_by(repartidor_nombre=rep).count()
    
    return render_template('reportes.html',
                         total_tickets=total_tickets,
                         tickets_pendientes=tickets_pendientes,
                         tickets_en_camino=tickets_en_camino,
                         tickets_entregados=tickets_entregados,
                         tickets_por_repartidor=tickets_por_repartidor)

@app.route('/ticket/<int:ticket_id>/asignar_repartidor', methods=['POST'])
@login_required
def asignar_repartidor(ticket_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Acceso no permitido'}), 403
    
    ticket = Ticket.query.get_or_404(ticket_id)
    repartidor = request.form.get('repartidor')
    
    if repartidor:
        ticket.repartidor = repartidor
        db.session.commit()
        
        # Emitir evento WebSocket
        socketio.emit('ticket_asignado', {
            'ticket_id': ticket.id,
            'repartidor': repartidor
        })
        
        return jsonify({'exito': True, 'mensaje': f'Ticket asignado a {repartidor}'})
    
    return jsonify({'error': 'Repartidor no especificado'}), 400

@app.route('/ticket/<int:ticket_id>/detalle')
@login_required
def detalle_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('detalle_ticket.html', ticket=ticket)

@app.route('/ticket/<int:ticket_id>/eliminar', methods=['POST'])
@login_required
def eliminar_ticket(ticket_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Acceso no permitido'}), 403
    
    ticket = Ticket.query.get_or_404(ticket_id)
    numero_ticket = ticket.numero
    
    db.session.delete(ticket)
    db.session.commit()
    
    # Emitir evento WebSocket
    socketio.emit('ticket_eliminado', {
        'ticket_id': ticket_id,
        'numero': numero_ticket
    })
    
    return jsonify({'exito': True, 'mensaje': 'Ticket eliminado correctamente'})

# ===== GESTIÓN DE USUARIOS =====

@app.route('/gestion_usuarios')
@login_required
@role_required('admin')
def gestion_usuarios():
    """Panel de gestión de usuarios para administradores"""
    usuarios = User.query.all()
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@app.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crear_usuario():
    """Crear nuevo usuario (solo admin)"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        role = request.form.get('role')
        
        # Validaciones
        if not all([username, email, password, nombre, role]):
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('crear_usuario'))
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('crear_usuario'))
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('crear_usuario'))
        
        # Crear nuevo usuario
        nuevo_usuario = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            nombre=nombre,
            role=role
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash(f'Usuario {nombre} creado exitosamente', 'success')
        return redirect(url_for('gestion_usuarios'))
    
    return render_template('crear_usuario.html')

@app.route('/usuario/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar_usuario(user_id):
    """Editar usuario existente (solo admin)"""
    usuario = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        role = request.form.get('role')
        nueva_password = request.form.get('nueva_password')
        
        # Validaciones
        if not all([username, email, nombre, role]):
            flash('Los campos username, email, nombre y role son obligatorios', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Verificar si el username ya existe (excluyendo el usuario actual)
        usuario_existente = User.query.filter_by(username=username).first()
        if usuario_existente and usuario_existente.id != user_id:
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Verificar si el email ya existe (excluyendo el usuario actual)
        email_existente = User.query.filter_by(email=email).first()
        if email_existente and email_existente.id != user_id:
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Actualizar usuario
        usuario.username = username
        usuario.email = email
        usuario.nombre = nombre
        usuario.role = role
        
        if nueva_password:
            usuario.password = generate_password_hash(nueva_password)
        
        db.session.commit()
        flash(f'Usuario {nombre} actualizado exitosamente', 'success')
        return redirect(url_for('gestion_usuarios'))
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuario/<int:user_id>/eliminar', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_usuario(user_id):
    """Eliminar usuario (solo admin)"""
    usuario = User.query.get_or_404(user_id)
    
    # No permitir eliminar al administrador principal
    if usuario.username == 'admin':
        flash('No se puede eliminar al administrador principal', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    # Verificar si el usuario tiene tickets asignados
    tickets_asignados = Ticket.query.filter_by(asignado_a=user_id).count()
    if tickets_asignados > 0:
        flash(f'No se puede eliminar el usuario. Tiene {tickets_asignados} tickets asignados', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    nombre_usuario = usuario.nombre
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'Usuario {nombre_usuario} eliminado exitosamente', 'success')
    return redirect(url_for('gestion_usuarios'))

@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        # Validaciones
        if not check_password_hash(current_user.password, password_actual):
            flash('La contraseña actual es incorrecta', 'danger')
            return redirect(url_for('cambiar_password'))
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas nuevas no coinciden', 'danger')
            return redirect(url_for('cambiar_password'))
        
        if len(nueva_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('cambiar_password'))
        
        # Actualizar contraseña
        current_user.password = generate_password_hash(nueva_password)
        db.session.commit()
        
        flash('Contraseña cambiada exitosamente', 'success')
        return redirect(url_for('panel'))
    
    return render_template('cambiar_password.html')

# ==========================================
# ENDPOINTS PARA CONSUMIR API DE BELGRANO AHORRO
# ==========================================

@app.route('/api/ahorro/productos', methods=['GET'])
@login_required
@role_required('admin')
def get_productos_ahorro():
    """Obtener productos desde Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        categoria = request.args.get('categoria')
        productos = api_client.get_productos(categoria)
        
        return jsonify({
            'status': 'success',
            'productos': productos,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo productos de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/pedido/<numero_pedido>', methods=['GET'])
@login_required
def get_pedido_ahorro(numero_pedido):
    """Obtener pedido específico desde Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        pedido = api_client.get_pedido(numero_pedido)
        
        if not pedido:
            return jsonify({
                'status': 'error',
                'error': 'Pedido no encontrado'
            }), 404
        
        return jsonify({
            'status': 'success',
            'pedido': pedido,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo pedido {numero_pedido} de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/pedido/<numero_pedido>/estado', methods=['PUT'])
@login_required
def actualizar_estado_pedido_ahorro(numero_pedido):
    """Actualizar estado de pedido en Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({
                'status': 'error',
                'error': 'Estado requerido'
            }), 400
        
        success = api_client.actualizar_estado_pedido(numero_pedido, nuevo_estado)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Estado actualizado a {nuevo_estado}',
                'numero_pedido': numero_pedido,
                'estado': nuevo_estado,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': 'No se pudo actualizar el estado'
            }), 500
        
    except Exception as e:
        logger.error(f"Error actualizando estado del pedido {numero_pedido}: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/sync/tickets', methods=['POST'])
@login_required
@role_required('admin')
def sync_tickets_to_ahorro():
    """Sincronizar tickets hacia Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        # Obtener todos los tickets
        tickets = Ticket.query.all()
        tickets_data = []
        
        for ticket in tickets:
            tickets_data.append({
                'numero_pedido': ticket.numero_pedido,
                'ticket_id': ticket.id,
                'estado': ticket.estado,
                'repartidor': ticket.repartidor,
                'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
                'fecha_actualizacion': ticket.fecha_actualizacion.isoformat() if ticket.fecha_actualizacion else None,
                'datos_completos': {
                    'id': ticket.id,
                    'numero_pedido': ticket.numero_pedido,
                    'cliente': ticket.cliente,
                    'productos': ticket.productos,
                    'total': ticket.total,
                    'estado': ticket.estado,
                    'repartidor': ticket.repartidor,
                    'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
                    'fecha_actualizacion': ticket.fecha_actualizacion.isoformat() if ticket.fecha_actualizacion else None
                }
            })
        
        success = api_client.sync_tickets_to_ahorro(tickets_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'{len(tickets_data)} tickets sincronizados',
                'tickets_synced': len(tickets_data),
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': 'Error en la sincronización'
            }), 500
        
    except Exception as e:
        logger.error(f"Error sincronizando tickets: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/test', methods=['GET'])
@login_required
@role_required('admin')
def test_ahorro_api():
    """Probar conexión con API de Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        # Probar health check
        health = api_client.health_check()
        
        # Probar obtención de productos
        productos = api_client.get_productos()
        
        return jsonify({
            'status': 'success',
            'health_check': health,
            'productos_test': {
                'status': 'success' if productos else 'error',
                'total': len(productos.get('productos', [])) if productos else 0
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error probando API de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Iniciando aplicación de tickets en puerto 5001...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
