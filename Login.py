import streamlit as st
import DashPedagogico as dp
import bcrypt
from config import engine  # importa a engine pronta
from sqlalchemy import text
import unicodedata
import hmac
import hashlib
import os
import logging
from typing import Optional, List, Union
from sqlalchemy.exc import OperationalError

# Obtém chave secreta do ambiente (igual ao Node.js)
HASH_SECRET = os.getenv("HASH_SECRET")

# ---------------------------
# Função para gerar (e-mail hash) do usuário
# ---------------------------
def hash_value(value: Union[str, None, List[Optional[str]]]) -> Union[str, None, List[Optional[str]]]:
    """
    Gera hash SHA256 com chave secreta (HMAC) para strings, None ou lista de strings/None.
    """
    
    if HASH_SECRET is None:
        raise ValueError("Chave de hash não fornecida")

    def normalize_and_hash(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        # Normalizar: remover acentos, espaços extras e converter para minúsculas
        val = (
            unicodedata.normalize("NFD", val)
            .encode("ascii", "ignore")
            .decode("utf-8")
            .strip()
            .lower()
        )
        # Criar HMAC SHA256
        return hmac.new(HASH_SECRET.encode(), val.encode(), hashlib.sha256).hexdigest()

    if value is None:
        return None
    if isinstance(value, list):
        return [normalize_and_hash(v) for v in value]
    
    return normalize_and_hash(value)

# ---------------------------------------------------
# Função para validar permissão de acesso ao dashboard
# ---------------------------------------------------
def validar_permissao(user_email_hash: str) -> bool:
    """
    Valida se o usuário tem permissão para acessar o dashboard.
    Apenas papéis 'GestorFederal', 'GestorEstadual' e 'GestorMunicipal' são aceitos.
    """
    permissoes_permitidas = {"GestorFederal", "GestorEstadual", "GestorMunicipal"}

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT r.name
                FROM auth.users u
                JOIN auth.user_roles ur ON u.id = ur.user_id
                JOIN auth.roles r ON ur.role_id = r.id
                WHERE u.email_hash = :email_hash
            """)
            # Executa a query e retorna todos os papéis (roles) do usuário como lista de tuplas (role_name,)
            roles = conn.execute(query, {"email_hash": user_email_hash}).fetchall()
            user_roles = {r[0] for r in roles}
            return bool(user_roles & permissoes_permitidas)

    except OperationalError as e:
        logging.error(f"Falha operacional no banco ao validar permissões: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado ao validar permissões: {e}")
        st.error("Ocorreu um erro inesperado.")
        return False

# ---------------------------
# Função para validar usuário
# ---------------------------
def autenticar_usuario(username: str, password: str) -> bool:
    """
    Valida o login do usuário contra o banco de dados.
    Retorna True se sucesso, False caso contrário.
    """

    try:
        # Normaliza entrada do usuário
        username = username.strip().lower()
        email_hash = hash_value(username)

        with engine.connect() as conn:
            query = text("SELECT password FROM auth.users WHERE email_hash = :u")
            result = conn.execute(query, {"u": email_hash}).fetchone()

        if not result:
            #st.error("Usuário ou senha inválidos.")
            return False

        senha_hash = result[0]

        if bcrypt.checkpw(password.encode("utf-8"), senha_hash.encode("utf-8")):
            return True
        else:
            #st.error("Usuário ou senha inválidos.")
            return False

    except OperationalError as e:
        logging.error(f"Falha operacional no banco: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        st.error("Ocorreu um erro inesperado.")
        return False

# ---------------------------
# Login no Streamlit
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.set_page_config(layout="wide")
    st.title("🔒 Login")

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if autenticar_usuario(username, password):
            email_hash = hash_value(username)
            if validar_permissao(email_hash):
                st.session_state.logged_in = True
                st.session_state.user = username
                st.success("Login realizado com sucesso, acesso liberado ao dashboard!")
                st.rerun()
            else:
                st.error("Você não tem permissão para acessar este dashboard.")
        else:
            st.error("Usuário ou senha inválidos")
else:
    if st.sidebar.button("Sair"):
       st.session_state.logged_in = False
       st.rerun()

    #st.sidebar.success(f"Bem-vindo(a), {st.session_state.user}!")
    st.sidebar.subheader(st.session_state.user)

    email_hash = hash_value(st.session_state.user)
    dp.dashboardPedegogico(email_hash)
