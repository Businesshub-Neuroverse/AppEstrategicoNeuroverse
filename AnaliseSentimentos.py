import streamlit as st
import pandas as pd
import cv2
from google.cloud import storage
from deepface import DeepFace
import numpy as np
from sqlalchemy import text
from config import engine
from sqlalchemy.exc import OperationalError
import logging
import matplotlib.pyplot as plt
import math

# ================================
# 🎯 Funções auxiliares
# ================================

def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    """Faz download de uma imagem do GCS e retorna os bytes."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    return blob.download_as_bytes()

def analisar_emocao(img_bytes: bytes):
    """Analisa a emoção dominante usando DeepFace com backend MTCNN."""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    resultados = DeepFace.analyze(
        img,
        actions=['emotion'],
        detector_backend="mtcnn",
        enforce_detection=True
    )

    if isinstance(resultados, dict):
        resultados = [resultados]

    return resultados, img

# ================================
# 🧠 Função principal
# ================================

def analiseDeSentimentos(email_hash=None):

    # -------------------------------
    # Configuração da página
    # -------------------------------
    st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
    st.title("🧠 Análise de Sentimentos dos Alunos")

    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------------
    # Consulta SQL
    # -------------------------------
    query = text("""
        SELECT 
            u.email_hash AS hash_email,
            s.name AS escola_nome,
            t.year AS turma_ano,
            a.name AS aluno_nome,
            av.status AS avaliacao_status,
            av.feelings_urls AS urls_imagens,
            cl.label AS classificacao_aluno
        FROM auth.users u
        JOIN auth.school_users su ON u.id = su.user_id
        JOIN core.schools s ON su.school_id = s.id
        JOIN core.school_classes t ON s.id = t.school_id
        JOIN core.children a ON t.id = a.class_id
        JOIN littera.children_avaliation av ON a.id = av.child_id
        JOIN littera.children_classification cl ON av.classification_id = cl.id
        WHERE av.status = 'Concluido' and av.feelings_urls is not null  
        AND u.email_hash = :email_hash
        ORDER BY av.classification_score
    """)

    try:
        df = pd.read_sql(query, engine, params={"email_hash": email_hash})
    except OperationalError as e:
        logging.error(f"Falha operacional ao conectar banco: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        return
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        st.error("Ocorreu um erro inesperado. Tente novamente mais tarde.")
        return

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    # Traduções de emoções
    traducoes_emocoes = {
        "angry": "Raiva",
        "disgust": "Aborrecida",
        "fear": "Medo",
        "happy": "Alegria",
        "sad": "Tristeza",
        "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    # -------------------------------
    # Quebra lista de imagens
    # -------------------------------
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    resultados_por_aluno = {}
    bucket_name = "littera_images"

    # Organiza por aluno
    for _, row in df_explodido.iterrows():
        aluno = row["aluno_nome"]
        escola = row["escola_nome"]
        file_name = row["url_imagem"]

        if (escola, aluno) not in resultados_por_aluno:
            resultados_por_aluno[(escola, aluno)] = []

        resultados_por_aluno[(escola, aluno)].append({
            "arquivo": file_name,
            "emocao": None,
            "detalhe": None,
            "imagem": None
        })

    # -------------------------------
    # Paginação
    # -------------------------------
    fotos_por_pagina = 21
    alunos = list(resultados_por_aluno.keys())
    total_paginas = math.ceil(len(alunos) / fotos_por_pagina)
    pagina_atual = st.number_input("Selecione a página", min_value=1, max_value=total_paginas, value=1, step=1)

    inicio = (pagina_atual - 1) * fotos_por_pagina
    fim = inicio + fotos_por_pagina
    alunos_pagina = alunos[inicio:fim]

    # -------------------------------
    # Processamento das imagens na página atual
    # -------------------------------
    for (escola, aluno) in alunos_pagina:
        fotos = resultados_por_aluno[(escola, aluno)]
        resumo_emocoes = []

        with st.expander(f"{escola} - {aluno}"):

            for j, foto in enumerate(fotos, start=1):
                file_name = foto["arquivo"]
                try:
                    # Baixa e analisa imagem somente agora
                    img_bytes = baixar_imagem_gcs(bucket_name, file_name)
                    resultados, img = analisar_emocao(img_bytes)
                    foto["detalhe"] = resultados
                    foto["imagem"] = img
                    emocao_dominante = resultados[0]['dominant_emotion']
                    foto["emocao"] = traducoes_emocoes[emocao_dominante]
                except ValueError:
                    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                    foto["imagem"] = img
                    foto["emocao"] = "Sem rosto detectado"
                    foto["detalhe"] = None
                except Exception as e:
                    logging.error(f"Erro ao processar imagem {file_name}: {e}")
                    foto["emocao"] = "Erro"
                    foto["detalhe"] = None

                resumo_emocoes.append(foto["emocao"])

                # -------------------------------
                # Exibição
                # -------------------------------
                col1, col2 = st.columns([1,1])
                with col1:
                    st.image(cv2.cvtColor(foto["imagem"], cv2.COLOR_BGR2RGB), caption=f"Foto {j}")
                with col2:
                    if foto["detalhe"] is None:
                        st.error(f"📸 Foto {j}: {foto['emocao']}")
                        continue

                    emocoes = foto["detalhe"][0]['emotion']
                    valores = [float(v) for v in emocoes.values()]  # garante float
                    labels = [traducoes_emocoes[e] for e in emocoes.keys()]

                    cores = [
                        "#E53935",  # Raiva
                        "#8E24AA",  # Aborrecida
                        "#3949AB",  # Medo
                        "#43A047",  # Alegria
                        "#FB8C00",  # Tristeza
                        "#FDD835",  # Surpresa
                        "#546E7A",  # Neutra
                    ]

                    fig, ax = plt.subplots(figsize=(6,4))
                    barras = ax.barh(labels, valores, color=cores)
                    ax.set_xlabel("Probabilidade (%)")
                    ax.set_title("Distribuição das Emoções")
                    ax.invert_yaxis()

                    for bar in barras:
                        width = bar.get_width()
                        ax.text(width + 1, bar.get_y() + bar.get_height()/2, f"{width:.1f}%", va='center')

                    fig.tight_layout()
                    st.success(f"📸 Foto {j} - Emoção Predominante: {foto['emocao']}")
                    st.pyplot(fig)
                    plt.close(fig)
