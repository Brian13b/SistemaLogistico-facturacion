# Imagen base de Python
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias del sistema y Python
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs certs cache

# Exponer el puerto
EXPOSE 8003

# Comando para iniciar la aplicación
CMD ["uvicorn", "src.api_main:app", "--host", "0.0.0.0", "--port", "8003"]
