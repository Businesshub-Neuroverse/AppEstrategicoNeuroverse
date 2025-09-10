# ---------------------------
# Dockerfile ajustado
# ---------------------------

# Imagem base oficial do Python
FROM python:3.11-slim

# Define diretório de trabalho dentro do container
WORKDIR /app-strategic-neuroverse

# Evita warnings de Python
ENV PYTHONUNBUFFERED=1

# Copia requirements primeiro para aproveitar cache
COPY requirements.txt .

# Instala dependências do sistema necessárias para algumas bibliotecas
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o container
COPY . .

# Expõe a porta para Cloud Run ou execução local
EXPOSE 8080

# Comando de execução (ajustado para rodar Streamlit na porta 8080)
CMD ["streamlit", "run", "Login.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
