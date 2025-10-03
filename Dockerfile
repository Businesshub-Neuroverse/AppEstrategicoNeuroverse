# ---------------------------
# Dockerfile otimizado
# ---------------------------

FROM python:3.11-slim

# Atualiza pacotes e instala dependências do sistema
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app-strategic-neuroverse

# Evita buffering de logs no Python
ENV PYTHONUNBUFFERED=1

# Copia requirements primeiro (para cache de camadas)
COPY requirements.txt .

# Atualiza instaladores do Python e instala dependências
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código
COPY . .

# Expõe porta para o Cloud Run
EXPOSE 8080

# Comando de inicialização (Streamlit)
CMD ["streamlit", "run", "Login.py", "--server.port=8080", "--server.headless=true"]
