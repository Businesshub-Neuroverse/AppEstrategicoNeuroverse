# Imagem base oficial do Python
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements primeiro (para aproveitar cache)
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do projeto
COPY AppEstrategicoNeuroverse/ AppEstrategicoNeuroverse/

# Expõe a porta do Cloud Run
EXPOSE 8080

# Comando de execução (ajustado para Cloud Run)
CMD ["streamlit", "run", "AppEstrategicoNeuroverse/Login.py", "--server.port=8080", "--server.address=0.0.0.0"]
