#!/usr/bin/env python3
"""
Script simple para iniciar la aplicación de tickets
"""
import os
import sys

def main():
    """Inicia la aplicación"""
    print("🚀 INICIANDO LA TICKETERA")
    print("=" * 50)
    
    # Verificar archivos
    if not os.path.exists('app.py'):
        print("❌ No se encontró app.py")
        return
    
    if not os.path.exists('belgrano_tickets.db'):
        print("❌ No se encontró belgrano_tickets.db")
        print("💡 Ejecuta: python crear_db_simple.py")
        return
    
    print("✅ Archivos verificados")
    print("🌐 Accede a: http://localhost:5001")
    print("🔐 Login con:")
    print("   👑 Admin: admin@belgranoahorro.com / admin123")
    print("   🚚 Flota: repartidor1@belgranoahorro.com / repartidor123")
    print("\n📝 Presiona Ctrl+C para detener")
    print("-" * 50)
    
    try:
        # Importar y ejecutar la aplicación
        from app import app, socketio
        print("✅ Aplicación importada correctamente")
        print("🚀 Iniciando servidor...")
        socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n⏹️ Aplicación detenida")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
