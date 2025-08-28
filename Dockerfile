# Dockerfile para Belgrano Tickets con Socket.IO optimizado
FROM python:3.9-slim

# Establecer variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV RENDER_ENVIRONMENT=production

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements_ticketera.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements_ticketera.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para logs
RUN mkdir -p /app/logs

# Exponer puerto
EXPOSE 5001

# Configurar health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/healthz || exit 1

# Hacer el script ejecutable
RUN chmod +x run.sh

# Comando para ejecutar la aplicación usando el script de inicio
CMD ["./run.sh"]
