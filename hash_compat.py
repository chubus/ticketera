#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funciones de compatibilidad de hash para Belgrano Tickets
"""

import hmac
import binascii
import hashlib
from werkzeug.security import check_password_hash, generate_password_hash

def verificar_password_compat(stored_hash: str, plain_password: str) -> bool:
    """Verifica password con compatibilidad para hashes 'scrypt:' heredados."""
    # Intento estándar con Werkzeug
    try:
        return check_password_hash(stored_hash, plain_password)
    except Exception:
        pass
    # Compatibilidad scrypt en formato: 'scrypt:N:r:p$salt_hex$digest_hex'
    try:
        if not stored_hash.startswith('scrypt:'):
            return False
        meta_rest = stored_hash.split(':', 1)[1]
        params_part, salt_hex, digest_hex = meta_rest.split('$')
        n_str, r_str, p_str = params_part.split(':')
        n = int(n_str)
        r = int(r_str)
        p = int(p_str)
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(digest_hex)
        dk = hashlib.scrypt(
            plain_password.encode('utf-8'),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected)
        )
        return hmac.compare_digest(dk, expected)
    except Exception as e:
        print(f"Error verificando hash scrypt: {e}")
        return False

def migrar_hash_si_corresponde(user_id: int, stored_hash: str, plain_password: str) -> None:
    """Si el hash previo es 'scrypt:' y la verificación fue válida, re-hashear con el esquema actual."""
    try:
        if stored_hash.startswith('scrypt:'):
            nuevo_hash = generate_password_hash(plain_password)
            # Importar db aquí para evitar imports circulares
            from models import db, User
            user = User.query.get(user_id)
            if user:
                user.password = nuevo_hash
                db.session.commit()
                print('🔄 Hash de contraseña migrado a formato actual para el usuario', user_id)
    except Exception as e:
        print(f"Error migrando hash: {e}")

def resetear_credenciales_admin():
    """Resetear credenciales de admin y flota"""
    try:
        from models import db, User
        
        # Resetear admin
        admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
        if admin:
            admin.password = generate_password_hash('admin123')
            admin.activo = True
            print(f"✅ Admin actualizado: {admin.email}")
        else:
            # Crear admin si no existe
            admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                nombre='Administrador',
                rol='admin',
                activo=True
            )
            db.session.add(admin)
            print(f"✅ Admin creado: {admin.email}")
        
        # Resetear usuarios flota
        flota_usuarios = [
            ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
            ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
            ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
            ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
            ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
        ]
        
        for username, email, nombre in flota_usuarios:
            flota_user = User.query.filter_by(email=email).first()
            if flota_user:
                flota_user.password = generate_password_hash('flota123')
                flota_user.activo = True
                print(f"✅ Flota actualizado: {email}")
            else:
                flota_user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash('flota123'),
                    nombre=nombre,
                    rol='flota',
                    activo=True
                )
                db.session.add(flota_user)
                print(f"✅ Flota creado: {email}")
        
        db.session.commit()
        print("✅ Credenciales reseteadas exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error reseteando credenciales: {e}")
        return False
