# Dockerfile optimizado para Belgrano Tickets - Render.com
FROM python:3.12-slim

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Establece el directorio de trabajo
WORKDIR /app

# Copia archivos de la aplicación de forma específica
COPY app.py ./
COPY models.py ./
COPY config_ticketera.py ./
COPY requirements_ticketera.txt ./
COPY start_ticketera.sh ./
COPY belgrano_client.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Instala las dependencias de Python de forma optimizada
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements_ticketera.txt

# Hace el script de inicio ejecutable
RUN chmod +x start_ticketera.sh

# Variables de entorno por defecto
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PORT=5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Comando de inicio
CMD ["./start_ticketera.sh"]
