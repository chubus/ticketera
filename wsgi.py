#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point para Gunicorn
"""

from app import app, socketio

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=10000, debug=False)
