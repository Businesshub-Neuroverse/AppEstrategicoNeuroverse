import streamlit as st
import DashPedagogico as dp
from urllib.parse import unquote

# Forçar tema claro definindo CSS customizado
st.markdown(
    """
    <style>
        /* Fundo da página */
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        /* Títulos */
        h1, h2, h3, h4, h5, h6 {
            color: #000000;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------
# Captura parâmetros da URL
# -----------------------
params = st.query_params
st.write("teste juju")
# Decodifica os parâmetros para evitar problemas com caracteres especiais
email_hash = unquote(params.get("email_hash", [None])[0]) if params.get("email_hash") else None
pagina = unquote(params.get("page", [None])[0]) if params.get("page") else None

st.write("Parâmetro email_hash:", email_hash)
st.write("Parâmetro page:", pagina)

# -----------------------
# Redirecionamento para página correta
# -----------------------
if pagina == "dash_ped":
    if not email_hash:
        st.error("Parâmetro 'email_hash' não fornecido na URL!")
        st.stop()
    else:
        dp.dashboardPedegogico(email_hash)
else:
    st.error("Parâmetro 'page' não fornecido ou página não encontrada!")
    st.stop()

