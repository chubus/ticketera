from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """Modelo de usuario para admin y flota"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' o 'flota'
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con tickets asignados
    tickets_asignados = db.relationship('Ticket', backref='repartidor_user', lazy=True, foreign_keys='Ticket.asignado_a')
    
    def __repr__(self):
        return f'<User {self.email}>'

class Ticket(db.Model):
    """Modelo de ticket para gestión de pedidos"""
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    cliente_nombre = db.Column(db.String(120), nullable=False)
    cliente_direccion = db.Column(db.String(200), nullable=False)
    cliente_telefono = db.Column(db.String(50), nullable=False)
    cliente_email = db.Column(db.String(120), nullable=False)
    productos = db.Column(db.Text, nullable=False)  # JSON string con productos y negocios
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, en_proceso, entregado, cancelado
    prioridad = db.Column(db.String(20), default='normal')  # baja, normal, alta, urgente
    indicaciones = db.Column(db.Text)
    asignado_a = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    repartidor_nombre = db.Column(db.String(50), nullable=True)  # Nombre del repartidor
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_asignacion = db.Column(db.DateTime, nullable=True)
    fecha_entrega = db.Column(db.DateTime, nullable=True)
    notas_repartidor = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Ticket {self.numero}>'

class Configuracion(db.Model):
    """Modelo para configuraciones del sistema"""
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.String(200))
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Configuracion {self.clave}>'
