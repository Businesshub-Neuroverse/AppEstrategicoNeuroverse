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

# ================================
# Configurações da página e estilo
# ================================
st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] {
        display: none !important;
    }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ================================
# Traduções de emoções
# ================================
TRADUCOES_EMOCOES = {
    "angry": "Raiva",
    "disgust": "Aborrecida",
    "fear": "Medo",
    "happy": "Alegria",
    "sad": "Tristeza",
    "surprise": "Surpresa",
    "neutral": "Neutra"
}

# ================================
# Funções auxiliares
# ================================
def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    return blob.download_as_bytes()

def analisar_emocao(img_bytes: bytes):
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

def gerar_grafico_emocoes(resultados):
    emocoes = resultados[0]['emotion']
    valores = list(emocoes.values())
    labels = [TRADUCOES_EMOCOES[e] for e in emocoes.keys()]
    cores = ["#E53935","#8E24AA","#3949AB","#43A047","#FB8C00","#FDD835","#546E7A"]

    fig, ax = plt.subplots(figsize=(6,4))
    barras = ax.barh(labels, valores, color=cores)
    ax.set_xlabel("Probabilidade (%)")
    ax.set_title("Distribuição das Emoções")
    ax.invert_yaxis()
    for bar in barras:
        width = bar.get_width()
        ax.text(width+1, bar.get_y()+bar.get_height()/2, f"{width:.1f}%", va='center')
    fig.tight_layout()
    return fig

# ================================
# Função cacheada: busca e analisa tudo de uma vez
# ================================
@st.cache_data(show_spinner=True)
def carregar_e_analisar(email_hash):
    # Consulta SQL
    query = text("""
        SELECT 
            u.email_hash AS hash_email,
            s.name AS escola_nome,
            a.name AS aluno_nome,
            av.feelings_urls AS urls_imagens
        FROM auth.users u
        JOIN auth.school_users su ON u.id = su.user_id
        JOIN core.schools s ON su.school_id = s.id
        JOIN core.school_classes t ON s.id = t.school_id
        JOIN core.children a ON t.id = a.class_id
        JOIN littera.children_avaliation av ON a.id = av.child_id
        WHERE av.status = 'Concluido' AND av.feelings_urls IS NOT NULL
        AND u.email_hash = :email_hash
        ORDER BY av.classification_score
    """)

    df = pd.read_sql(query, engine, params={"email_hash": email_hash})
    if df.empty:
        return []

    # Explode urls
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    # Agrupa fotos por aluno
    alunos_dict = {}
    for _, row in df_explodido.iterrows():
        chave = (row["escola_nome"], row["aluno_nome"])
        alunos_dict.setdefault(chave, []).append(row["url_imagem"])

    bucket_name = "littera_images"
    alunos_resultados = []

    # Barra de progresso global
    total_alunos = len(alunos_dict)
    global_bar = st.progress(0, text="Carregando e analisando alunos...")

    for idx, ((escola, aluno), fotos) in enumerate(alunos_dict.items(), start=1):
        fotos_resultados = []
        individual_bar = st.progress(0, text=f"Analisando {aluno}...")

        for j, file_name in enumerate(fotos[:3], start=1):  # só 3 fotos
            try:
                img_bytes = baixar_imagem_gcs(bucket_name, file_name)
                resultados, img = analisar_emocao(img_bytes)
                emocao_dominante = max(resultados[0]['emotion'], key=resultados[0]['emotion'].get)
                emocao_dominante_pt = TRADUCOES_EMOCOES[emocao_dominante]

                # Desenhar bounding box
                img_bgr_com_bbox = img.copy()
                for face in resultados:
                    region = face.get('region', {})
                    if all(k in region for k in ['x','y','w','h']):
                        x, y, w, h = region['x'], region['y'], region['w'], region['h']
                        cv2.rectangle(img_bgr_com_bbox, (x,y), (x+w, y+h), (0,255,0), 2)

                fotos_resultados.append({
                    "file": file_name,
                    "img": img_bgr_com_bbox,
                    "resultados": resultados,
                    "emocao_dominante_pt": emocao_dominante_pt
                })
            except Exception as e:
                logging.error(f"Erro ao processar {file_name} de {aluno}: {e}")

            individual_bar.progress(j/3, text=f"Analisando {aluno} ({j}/3)")

        individual_bar.empty()
        alunos_resultados.append({
            "escola": escola,
            "aluno": aluno,
            "fotos": fotos_resultados
        })

        global_bar.progress(idx/total_alunos, text=f"Processando {idx}/{total_alunos} alunos...")

    global_bar.empty()
    return alunos_resultados

# ================================
# Função principal
# ================================
def analiseDeSentimentos(email_hash=None):
    st.title("🧠 Análise de Sentimentos dos Alunos")

    try:
        alunos_resultados = carregar_e_analisar(email_hash)
    except OperationalError as e:
        logging.error(f"Erro de conexão: {e}")
        st.error("Erro ao conectar ao banco de dados.")
        return
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        st.error("Ocorreu um erro inesperado.")
        return

    if not alunos_resultados:
        st.warning("Nenhum registro encontrado.")
        return

    for aluno_data in alunos_resultados:
        escola = aluno_data["escola"]
        aluno = aluno_data["aluno"]
        fotos = aluno_data["fotos"]

        # Pega as 3 emoções predominantes
        emocoes_titulo = [foto["emocao_dominante_pt"] for foto in fotos]
        emocoes_str = ", ".join(emocoes_titulo) if emocoes_titulo else "Sem emoções detectadas"

        with st.expander(f"📌 {escola} — {aluno} | Emoções: {emocoes_str}"):
            for i, foto_data in enumerate(fotos, start=1):
                col1, col2 = st.columns([1,1])
                with col1:
                    st.image(cv2.cvtColor(foto_data["img"], cv2.COLOR_BGR2RGB), caption=f"Foto {i}")
                with col2:
                    st.success(f"Emoção predominante: {foto_data['emocao_dominante_pt']}")
                    fig = gerar_grafico_emocoes(foto_data["resultados"])
                    st.pyplot(fig)
                    plt.close(fig)
