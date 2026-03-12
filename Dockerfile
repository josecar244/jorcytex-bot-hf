# Usa una imagen oficial de Python ligera
FROM python:3.11-slim

# Establecer variables de entorno para evitar archivos .pyc y asegurar logs instantáneos
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar rquirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Exponer el puerto que usa Hugging Face Spaces (7860)
EXPOSE 7860

# Comando para iniciar la aplicación usando uvicorn
# HF Spaces inyecta el puerto 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 7860"]
