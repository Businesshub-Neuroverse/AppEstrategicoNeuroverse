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
from collections import Counter

# ================================
# CSS para título no topo
# ================================
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

st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
st.title("🧠 Análise de Sentimentos dos Alunos")

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

def gerar_grafico_emocoes(resultados, traducoes_emocoes):
    emocoes = resultados[0]['emotion']
    valores = list(emocoes.values())
    labels = [traducoes_emocoes[e] for e in emocoes.keys()]

    cores = ["#E53935","#8E24AA","#3949AB","#43A047","#FB8C00","#FDD835","#546E7A"]

    fig, ax = plt.subplots(figsize=(6,4))
    barras = ax.barh(labels, valores, color=cores)
    ax.set_xlabel("Probabilidade (%)")
    ax.set_title(f"Distribuição das Emoções")
    ax.invert_yaxis()
    for bar in barras:
        width = bar.get_width()
        ax.text(width+1, bar.get_y()+bar.get_height()/2, f"{width:.1f}%", va='center')
    fig.tight_layout()
    return fig

# ================================
# Cache para análise das imagens
# ================================
@st.cache_data(show_spinner=False)
def carregar_e_analisar_todas(bucket_name, alunos_dict, traducoes_emocoes):
    todas_analises = {}
    total_fotos = sum(len(fotos) for fotos in alunos_dict.values())
    progresso_global = 0

    progresso_placeholder = st.empty()
    barra_global = st.progress(0, text="Carregando e analisando todas as imagens...")

    for (escola, aluno), fotos in alunos_dict.items():
        todas_analises[(escola, aluno)] = []
        for idx, foto in enumerate(fotos, start=1):
            try:
                img_bytes = baixar_imagem_gcs(bucket_name, foto)
                resultados, img = analisar_emocao(img_bytes)
                emocao_dominante = max(resultados[0]['emotion'], key=resultados[0]['emotion'].get)
                todas_analises[(escola, aluno)].append({
                    "img_bytes": img_bytes,
                    "img": img,
                    "resultados": resultados,
                    "emocao_dominante": emocao_dominante
                })
            except ValueError:
                img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                todas_analises[(escola, aluno)].append({
                    "img_bytes": img_bytes,
                    "img": img,
                    "resultados": None,
                    "emocao_dominante": "Sem rosto detectado"
                })
            except Exception as e:
                logging.error(f"Erro ao processar {foto}: {e}")
                continue

            progresso_global += 1
            barra_global.progress(progresso_global / total_fotos,
                                 text=f"Processando {progresso_global}/{total_fotos} imagens...")

    barra_global.empty()
    return todas_analises

# ================================
# Função principal que você chama
# ================================
def analiseDeSentimentos(email_hash):
    # ================================
    # Consulta SQL
    # ================================
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
        return

    traducoes_emocoes = {
        "angry": "Raiva",
        "disgust": "Aborrecida",
        "fear": "Medo",
        "happy": "Alegria",
        "sad": "Tristeza",
        "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    # Explode urls de imagens
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    # Agrupa fotos por aluno
    alunos_dict = {}
    for _, row in df_explodido.iterrows():
        chave = (row["escola_nome"], row["aluno_nome"])
        alunos_dict.setdefault(chave, []).append(row["url_imagem"])

    bucket_name = "littera_images"

    # Carrega e analisa todas as imagens
    todas_analises = carregar_e_analisar_todas(bucket_name, alunos_dict, traducoes_emocoes)

    # Exibição dos resultados
    progresso_placeholder = st.empty()
    total_alunos = len(todas_analises)
    for idx, ((escola, aluno), fotos_info) in enumerate(todas_analises.items(), start=1):
        # Calcula as 3 emoções predominantes
        emos = [f["emocao_dominante"] for f in fotos_info if f["emocao_dominante"] != "Sem rosto detectado"]
        top3 = [e for e,_ in Counter(emos).most_common(3)]
        top3_str = " | ".join(top3) if top3 else "Sem rosto detectado"

        with st.expander(f"{escola} - {aluno} | Emoções predominantes: {top3_str}", expanded=True):
            barra_aluno = st.progress(0, text=f"Processando {aluno}...")

            for j, foto_info in enumerate(fotos_info, start=1):
                img_bgr_com_bbox = foto_info["img"].copy()
                resultados = foto_info["resultados"]

                # Desenha bounding box se houver rosto
                if resultados is not None:
                    for face in resultados:
                        region = face.get('region', {})
                        if all(k in region for k in ['x','y','w','h']):
                            x, y, w, h = region['x'], region['y'], region['w'], region['h']
                            cv2.rectangle(img_bgr_com_bbox, (x,y), (x+w, y+h), (0,255,0), 2)

                fig = gerar_grafico_emocoes(resultados, traducoes_emocoes) if resultados else None

                col1, col2 = st.columns([1,1])
                with col1:
                    st.image(cv2.cvtColor(img_bgr_com_bbox, cv2.COLOR_BGR2RGB), caption=f"Foto {j}")
                with col2:
                    st.success(f"📸 Emoção predominante: {foto_info['emocao_dominante']}")
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)

                barra_aluno.progress(j/len(fotos_info), text=f"Processando {j}/{len(fotos_info)} fotos de {aluno}...")

            barra_aluno.empty()
        progresso_placeholder.progress(idx / total_alunos, text=f"Processando {idx}/{total_alunos} alunos...")
    progresso_placeholder.empty()
