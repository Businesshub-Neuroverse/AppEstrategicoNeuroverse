# Importa as bibliotecas necessárias
import streamlit as st                 # Biblioteca principal para criar aplicações web interativas em Python
from urllib.parse import unquote       # Função para decodificar parâmetros da URL (ex: remover %20 e etc.)

# -----------------------
# Captura e trata os parâmetros da URL
# -----------------------
params = st.query_params                           # Obtém os parâmetros da URL como um dicionário
email_hash = unquote(params.get("email_hash", "")) # Lê o parâmetro 'email_hash' e decodifica, se existir
pagina = unquote(params.get("page", ""))           # Lê o parâmetro 'page' e decodifica, se existir

#email_hash = "b9a809faf21409795d942a19cce14b3a4ae94a090d5779c17981a22274bccc0a"  #SE
#pagina = "mapa_escolas"

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
    if not email_hash:                                  # ... mas não houver 'email_hash' informado...
        st.error("Parâmetro 'email_hash' não fornecido na URL!")  # ... mostra mensagem de erro
        st.stop()                                       # E para a execução da aplicação
    else:
        import AnaliseSentimentos as ans    # Módulo (arquivo .py) que contém a função analiseDeSentimentos
        ans.analiseDeSentimentos(email_hash)    
elif pagina == "mapa_escolas":   
        import DashMapaEscolas as mpe    # Módulo (arquivo .py) que contém a função analiseDeSentimentos
        mpe.escolasNoMapa()    
else:
    # Caso 'page' não seja 'dash_ped' ou não exista, mostra mensagem de erro
    st.error("Parâmetro 'page' não fornecido ou página não encontrada!")
    st.stop()  # Para a execução da aplicação










