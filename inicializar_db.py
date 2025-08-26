#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización robusto para la base de datos de Belgrano Tickets
"""

import os
import sys
from datetime import datetime

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from werkzeug.security import generate_password_hash
from models import db, User, Ticket, Configuracion

def crear_app():
    """Crear aplicación Flask para inicialización"""
    app = Flask(__name__)
    
    # Configuración de base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    print(f"🗄️ Ruta de base de datos: {db_path}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'
    
    # Inicializar extensiones
    db.init_app(app)
    
    return app

def inicializar_base_datos():
    """Inicializar base de datos con datos de prueba"""
    app = crear_app()
    
    with app.app_context():
        try:
            print("🔧 Inicializando base de datos...")
            
            # Crear todas las tablas
            db.create_all()
            print("✅ Tablas creadas correctamente")
            
            # Verificar si ya existen usuarios
            usuarios_existentes = User.query.count()
            print(f"📊 Usuarios existentes: {usuarios_existentes}")
            
            if usuarios_existentes == 0:
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
                    },
                    {
                        'clave': 'max_tickets_por_repartidor',
                        'valor': '10',
                        'descripcion': 'Máximo número de tickets por repartidor'
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
                
                # Crear tickets de prueba
                tickets_prueba = [
                    {
                        'numero': 'TICK-001',
                        'cliente_nombre': 'Juan Pérez',
                        'cliente_direccion': 'Av. Belgrano 123, CABA',
                        'cliente_telefono': '11-1234-5678',
                        'cliente_email': 'juan@ejemplo.com',
                        'productos': '{"productos": [{"nombre": "Arroz", "cantidad": 2, "precio": 150}]}',
                        'estado': 'pendiente',
                        'prioridad': 'normal',
                        'indicaciones': 'Entregar en horario de 9 a 18hs'
                    },
                    {
                        'numero': 'TICK-002',
                        'cliente_nombre': 'María García',
                        'cliente_direccion': 'Calle Corrientes 456, CABA',
                        'cliente_telefono': '11-8765-4321',
                        'cliente_email': 'maria@ejemplo.com',
                        'productos': '{"productos": [{"nombre": "Leche", "cantidad": 3, "precio": 200}]}',
                        'estado': 'en_proceso',
                        'prioridad': 'alta',
                        'indicaciones': 'Llamar antes de llegar'
                    }
                ]
                
                for ticket_data in tickets_prueba:
                    ticket = Ticket(
                        numero=ticket_data['numero'],
                        cliente_nombre=ticket_data['cliente_nombre'],
                        cliente_direccion=ticket_data['cliente_direccion'],
                        cliente_telefono=ticket_data['cliente_telefono'],
                        cliente_email=ticket_data['cliente_email'],
                        productos=ticket_data['productos'],
                        estado=ticket_data['estado'],
                        prioridad=ticket_data['prioridad'],
                        indicaciones=ticket_data['indicaciones'],
                        fecha_creacion=datetime.utcnow()
                    )
                    db.session.add(ticket)
                    print(f"✅ Ticket {ticket_data['numero']} creado")
                
                # Commit de todos los cambios
                db.session.commit()
                print("🎉 Inicialización completada exitosamente")
                
            else:
                print("✅ Usuarios ya existen, saltando creación")
            
            # Verificar datos finales
            total_usuarios = User.query.count()
            total_tickets = Ticket.query.count()
            total_configs = Configuracion.query.count()
            
            print(f"\n📊 RESUMEN DE BASE DE DATOS:")
            print(f"   • Usuarios: {total_usuarios}")
            print(f"   • Tickets: {total_tickets}")
            print(f"   • Configuraciones: {total_configs}")
            
            # Mostrar usuarios creados
            usuarios = User.query.all()
            print(f"\n👥 USUARIOS EN EL SISTEMA:")
            for usuario in usuarios:
                print(f"   • {usuario.nombre} ({usuario.email}) - Role: {usuario.role}")
            
            print(f"\n🔐 CREDENCIALES DE ACCESO:")
            print(f"   • Admin: admin@belgranoahorro.com / admin123")
            print(f"   • Flota: repartidor1@belgranoahorro.com / flota123")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en inicialización: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 INICIALIZADOR DE BASE DE DATOS - BELGRANO TICKETS")
    print("=" * 60)
    
    success = inicializar_base_datos()
    
    if success:
        print("\n✅ Base de datos inicializada correctamente")
        print("🎯 El sistema está listo para usar")
    else:
        print("\n❌ Error al inicializar la base de datos")
        sys.exit(1)
