# Configuración de Gunicorn para Belgrano Tickets

import os

# Configuración básica
bind = "0.0.0.0:{}".format(os.environ.get('PORT', 10000))
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configuración de la aplicación
preload_app = True
worker_connections = 1000

# Configuración de seguridad
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Configuración de procesos
worker_tmp_dir = "/dev/shm"
