import streamlit as st
import DashPedagogico as dp
import bcrypt
from config import engine  # importa a engine pronta
from sqlalchemy import text
import unicodedata
import hmac
import hashlib
import os
from typing import Optional, List, Union

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

    Args:
        user_email_hash (str): Hash do e-mail do usuário autenticado.

    Returns:
        bool: True se o usuário tiver permissão, False caso contrário.
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
            result = conn.execute(query, {"email_hash": user_email_hash}).fetchone()

            if result:
                role_name = result[0]
                return role_name in permissoes_permitidas

            return False  # Usuário não encontrado ou sem role vinculada

    except Exception as e:
        st.error(f"Erro ao validar permissões: {e}")
        return False

# ---------------------------
# Função para validar usuário
# ---------------------------
def autenticar_usuario(username: str, password: str) -> bool:
    """
    Valida o login do usuário contra o banco de dados.
    Retorna True se sucesso, False se falhar.
    """

    try:
        email_hash = hash_value(username)  # transforma email em hash
        with engine.connect() as conn:
            query = text("SELECT password FROM auth.users WHERE email_hash = :u")
            result = conn.execute(query, {"u": email_hash}).fetchone()

        if not result:
            # Usuário não encontrado
            return False

        senha_hash = result[0]

        if bcrypt.checkpw(password.encode("utf-8"), senha_hash.encode("utf-8")):
            return True
        else:
            return False

    except Exception as e:
        # Em produção, logue o erro em vez de mostrar
        st.error(f"Erro ao autenticar: {e}")
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

