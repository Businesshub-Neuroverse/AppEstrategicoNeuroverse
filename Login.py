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

# Pega os parâmetros da URL
params = st.experimental_get_query_params()

# Acessa o email_hash (se existir)
email_hash = params.get("email_hash", [None])[0]

# Acessa a página (se existir)
pagina = params.get("page", [None])[0]


st.write("paramento email_hash", email_hash)

st.write("paramento página", pagina)
# Chama a função passando o email_hash
#dashboardPedegogico(email_hash=email_hash)


#dp.dashboardPedegogico(email_hash)

