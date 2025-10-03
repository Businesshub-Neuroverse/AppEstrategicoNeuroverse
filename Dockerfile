# ---------------------------
# Dockerfile otimizado
# ---------------------------

# Imagem base oficial do Python
FROM python:3.11-slim

# Instalar dependências do sistema necessárias para OpenCV e outras libs
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho dentro do container
WORKDIR /app-strategic-neuroverse

# Evita warnings de Python
ENV PYTHONUNBUFFERED=1

# Copia requirements primeiro para aproveitar cache de build
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o container
COPY . .

# Expõe a porta para Cloud Run ou execução local
EXPOSE 8080

# Comando de execução para o Streamlit
CMD ["streamlit", "run", "Login.py", "--server.port=8080", "--server.headless=true"]
