#!/usr/bin/env python3
print("🧪 Probando registro de blueprints...")

import sys
sys.argv[0] = 'actualizar_db.py'

try:
    from app import app
    print("✅ SUCCESS: App importada sin registrar blueprints")
except Exception as e:
    print(f"❌ ERROR: {e}")
