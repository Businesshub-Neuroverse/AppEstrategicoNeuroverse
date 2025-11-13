# config.py
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# -----------------------------
# 🔹 Configuração de log padrão
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------------
# 🔹 Carrega .env local (se existir)
# -----------------------------
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("🔹 .env carregado para ambiente local")

# -----------------------------
# 🔹 Busca variáveis de ambiente
# -----------------------------
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASS, DB_HOST, DB_NAME]):
    raise ValueError("Alguma variável de conexão do banco não está definida!")

# -----------------------------
# 🔹 Cria engine SQLAlchemy
# -----------------------------
DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

inicio_conexao = time.time()
engine = create_engine(
    DB_URI,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True
)
logging.info(f"✅ Engine criada com sucesso em {time.time() - inicio_conexao:.3f}s")

# -----------------------------
# 🕒 Decorador genérico para medir tempo
# -----------------------------
def medir_tempo(descricao="Execução"):
    """
    Decorador para medir o tempo de qualquer função.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            inicio = time.time()
            logging.info(f"⏱️ {descricao} iniciada...")
            resultado = func(*args, **kwargs)
            duracao = time.time() - inicio
            logging.info(f"✅ {descricao} concluída em {duracao:.3f}s")
            return resultado
        return wrapper
    return decorator

# -----------------------------
# 🧠 Função auxiliar para medir tempo de conexão e query
# -----------------------------
@medir_tempo("Conexão e execução de query")
def executar_query(query_text, params=None):
    """
    Executa uma query SQL e mede separadamente o tempo de conexão e de execução.
    Retorna o DataFrame com os resultados.
    """
    import pandas as pd
    from sqlalchemy import text

    # Se o parâmetro vier como TextClause, converte para string
    if not isinstance(query_text, str):
        query_text = str(query_text)

    inicio_conn = time.time()
    with engine.connect() as conn:
        tempo_conexao = time.time() - inicio_conn
        logging.info(f"🔌 Tempo para abrir conexão: {tempo_conexao:.3f}s")

        inicio_query = time.time()
        df = pd.read_sql(text(query_text), conn, params=params)
        tempo_query = time.time() - inicio_query
        logging.info(f"📊 Tempo para executar query: {tempo_query:.3f}s")

    return df
