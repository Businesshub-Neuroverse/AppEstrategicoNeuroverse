# Importa as bibliotecas necessárias
import streamlit as st                 # Biblioteca principal para criar aplicações web interativas em Python
from urllib.parse import unquote       # Função para decodificar parâmetros da URL (ex: remover %20 e etc.)

# -----------------------
# Forçar tema claro (branco) com CSS customizado
# -----------------------
st.markdown("""
<style>
/* Define o fundo da aplicação como branco e o texto como preto */
.stApp { 
    background-color: #FFFFFF; 
    color: #000000; 
}

/* Define os títulos (h1, h2, etc.) como preto */
h1,h2,h3,h4,h5,h6 { 
    color: #000000; 
}

/* Define os campos de texto e número com fundo branco e texto preto */
.stTextInput input, .stNumberInput input {
    background-color: #FFFFFF;
    color: #000000;
}
</style>
""", unsafe_allow_html=True)   # unsafe_allow_html=True permite inserir HTML/CSS personalizado

# -----------------------
# Captura e trata os parâmetros da URL
# -----------------------
params = st.query_params                           # Obtém os parâmetros da URL como um dicionário
email_hash = unquote(params.get("email_hash", "")) # Lê o parâmetro 'email_hash' e decodifica, se existir
pagina = unquote(params.get("page", ""))           # Lê o parâmetro 'page' e decodifica, se existir

# Exibe os valores capturados na tela (para depuração)
#st.write("Parâmetro email_hash:", email_hash)
#st.write("Parâmetro page:", pagina)

# -----------------------
# Lógica de roteamento: decide o que exibir com base no parâmetro 'page'
# -----------------------
if pagina == "dash_ped":                                # Se a página solicitada for 'dash_ped'...
    if not email_hash:                                  # ... mas não houver 'email_hash' informado...
        st.error("Parâmetro 'email_hash' não fornecido na URL!")  # ... mostra mensagem de erro
        st.stop()                                       # E para a execução da aplicação
    else:
        import DashPedagogico as dp     # Módulo (arquivo .py) que contém a função dashboardPedegogico
        dp.dashboardPedagogico(email_hash)    
elif pagina == "analise_sentimento":   
           # Caso contrário, carrega o dashboard pedagógico
    if not email_hash:                                  # ... mas não houver 'email_hash' informado...
        st.error("Parâmetro 'email_hash' não fornecido na URL!")  # ... mostra mensagem de erro
        st.stop()                                       # E para a execução da aplicação
    else:
        import AnaliseSentimentos as ans    # Módulo (arquivo .py) que contém a função analiseDeSentimentos
        ans.analiseDeSentimentos(email_hash)    
else:
    # Caso 'page' não seja 'dash_ped' ou não exista, mostra mensagem de erro
    st.error("Parâmetro 'page' não fornecido ou página não encontrada!")
    st.stop()  # Para a execução da aplicação











