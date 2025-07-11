# Usa una imagen oficial de Python como base
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala uv
RUN pip install --no-cache-dir uv

# Copia los archivos de configuración de uv
COPY pyproject.toml  ./

# Instala las dependencias usando uv
RUN uv sync

# Copia el código fuente de la aplicación
COPY . .

# Puerto que usará Cloud Run
ENV PORT=8080

# Comando para iniciar el servidor usando uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
