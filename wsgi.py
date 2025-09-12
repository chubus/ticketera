#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point para Gunicorn
"""

from app import app

# Aplicación WSGI para Gunicorn
application = app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000, debug=False)
