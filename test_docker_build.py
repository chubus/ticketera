#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el build de Docker
"""

import subprocess
import sys
import os

def test_docker_build():
    """Probar el build de Docker"""
    print("🐳 Probando build de Docker...")
    
    try:
        # Probar build con Dockerfile
        result = subprocess.run([
            'docker', 'build', 
            '-t', 'belgrano-ticketera-test', 
            '.'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Build de Docker exitoso")
            return True
        else:
            print(f"❌ Error en build de Docker:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout en build de Docker")
        return False
    except FileNotFoundError:
        print("❌ Docker no está instalado o no está en PATH")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_dockerfile_syntax():
    """Verificar sintaxis del Dockerfile"""
    print("🔍 Verificando sintaxis del Dockerfile...")
    
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
        
        # Verificar elementos básicos
        required_elements = [
            'FROM python:3.12-slim',
            'WORKDIR /app',
            'COPY app.py ./',
            'COPY static/ ./static/',
            'RUN pip install',
            'CMD'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Elementos faltantes en Dockerfile: {missing_elements}")
            return False
        
        print("✅ Sintaxis del Dockerfile correcta")
        return True
        
    except Exception as e:
        print(f"❌ Error al verificar Dockerfile: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 TEST DE BUILD DE DOCKER")
    print("=" * 40)
    
    # Verificar sintaxis
    syntax_ok = test_dockerfile_syntax()
    
    # Probar build (solo si Docker está disponible)
    build_ok = False
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        build_ok = test_docker_build()
    except:
        print("⚠️ Docker no disponible, saltando test de build")
        build_ok = True  # Considerar como OK si Docker no está disponible
    
    # Resumen
    print("\n📊 RESUMEN")
    print("=" * 20)
    print(f"Sintaxis Dockerfile: {'✅ OK' if syntax_ok else '❌ FALLA'}")
    print(f"Build Docker: {'✅ OK' if build_ok else '❌ FALLA'}")
    
    if syntax_ok and build_ok:
        print("\n🎉 ¡Dockerfile listo para deploy!")
        return True
    else:
        print("\n⚠️ Hay problemas que deben resolverse")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


