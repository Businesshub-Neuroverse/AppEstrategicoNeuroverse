import streamlit as st
import DashPedagogico as dp

# -----------------------
# Forçar tema claro (branco) com CSS customizado
# -----------------------
st.markdown("""
<style>
/* Fundo da página */
.stApp { 
    background-color: #FFFFFF; 
    color: #000000; 
}
/* Títulos */
h1,h2,h3,h4,h5,h6 { 
    color: #000000; 
}
/* Inputs e botões */
.stTextInput input, .stNumberInput input {
    background-color: #FFFFFF;
    color: #000000;
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# Captura parâmetros da URL
# -----------------------
params = st.query_params  # Não chamar como função!
email_hash = params.get("email_hash", [None])[0]  # Pega o primeiro valor se houver
pagina = params.get("page", [None])[0]           # Pega o primeiro valor se houver

# -----------------------
# Debug (opcional)
# -----------------------
st.write("Parâmetro email_hash:", email_hash)
st.write("Parâmetro page:", pagina)

# -----------------------
# Validação e chamada da função
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
