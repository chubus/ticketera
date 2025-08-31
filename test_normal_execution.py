#!/usr/bin/env python3
print("🧪 Probando ejecución normal de la app...")

import sys
sys.argv[0] = 'app.py'

try:
    from app import app
    blueprints = list(app.blueprints.keys())
    print(f"📋 Blueprints registrados: {blueprints}")
    
    if 'devops' in blueprints:
        print("✅ SUCCESS: Blueprint de DevOps se registró correctamente")
    else:
        print("❌ ERROR: Blueprint de DevOps NO se registró")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
