# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# -----------------------------
# 🔹 Carrega .env local se existir
# -----------------------------
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("🔹 .env carregado para ambiente local")

# -----------------------------
# 🔹 Busca variáveis de ambiente (local ou GCP)
# -----------------------------
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # default 5432
DB_NAME = os.getenv("DB_NAME")

# -----------------------------
# 🔹 Validação mínima
# -----------------------------
if not all([DB_USER, DB_PASS, DB_HOST, DB_NAME]):
    raise ValueError("Alguma variável de conexão do banco não está definida!")

# -----------------------------
# 🔹 URI do SQLAlchemy
# -----------------------------
#DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Monta a URL no formato correto para Unix Socket
DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={DB_HOST}"

# -----------------------------
# 🔹 Cria engine do SQLAlchemy
# -----------------------------
#engine = create_engine(DB_URI, echo=False, future=True)
engine = create_engine(
    DB_URI, #String de conexão para o banco de dados (ex: "postgresql+psycopg2://user:pass@host:port/dbname")
    pool_size=5, #mantém 5 conexões "fixas" abertas.
    max_overflow=10, #pode abrir até mais 10 extras, se necessário.
    pool_timeout=30, #espera até 30s por uma conexão livre antes de lançar erro.
    pool_recycle=300,  #recicla conexões a cada 5 min para evitar "stale connections" (desconexão inesperada pelo servidor).
    pool_pre_ping=True #testa se a conexão ainda está viva antes de usar
)

print("✅ Engine criada com sucesso!")




