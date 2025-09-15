import streamlit as st
import DashPedagogico as dp

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
st.write("teste novidades")
# -----------------------
# Captura parâmetros da URL
# -----------------------
params = st.query_params
email_hash = params.get("email_hash", [None])[0]
pagina = params.get("page", [None])[0] or ""


if pagina == "dash_ped":
    if not email_hash:
        st.error("Parâmetro 'email_hash' não fornecido na URL!")
        st.stop()
    else:
        dp.dashboardPedegogico(email_hash)
else:
    st.error("Parâmetro 'page' não fornecido na URL - Página não Encontrada!")
    st.stop()



