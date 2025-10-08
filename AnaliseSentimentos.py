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
# Funções auxiliares
# ================================

def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    """Baixa a imagem do GCS"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    return blob.download_as_bytes()

def analisar_emocao(img_bytes: bytes):
    """Analisa emoção da imagem usando DeepFace"""
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

def desenhar_bbox(img, resultados):
    """Desenha bounding box nas faces"""
    img_copy = img.copy()
    if resultados is not None:
        for face in resultados:
            region = face.get('region', {})
            if all(k in region for k in ['x','y','w','h']):
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                cv2.rectangle(img_copy, (x,y), (x+w, y+h), (0,255,0), 2)
    return img_copy

# ================================
# Função principal
# ================================

def analiseDeSentimentos(email_hash=None):
    # ====================
    # CSS topo fixo
    # ====================
    st.markdown("""
        <style>
        [data-testid="stHeader"], div[role="banner"] { display: none !important; }
        .stApp { padding-top: 0 !important; margin-top: 0 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
    st.title("🧠 Análise de Sentimentos dos Alunos")

    # ====================
    # Consulta SQL
    # ====================
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
    except Exception as e:
        logging.error(f"Erro ao consultar banco: {e}")
        st.error("Erro ao consultar banco de dados")
        return

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    traducoes_emocoes = {
        "angry": "Raiva", "disgust": "Aborrecida", "fear": "Medo",
        "happy": "Alegria", "sad": "Tristeza", "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    # ====================
    # Explode urls
    # ====================
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split":"url_imagem"})

    # Agrupa fotos por aluno
    alunos_dict = {}
    for _, row in df_explodido.iterrows():
        chave = (row["escola_nome"], row["aluno_nome"])
        alunos_dict.setdefault(chave, []).append(row["url_imagem"])

    bucket_name = "littera_images"
    fotos_por_pagina = 15

    # Flatten fotos
    flat_list = []
    for chave, fotos in alunos_dict.items():
        for foto in fotos:
            flat_list.append((chave[0], chave[1], foto))  # (escola, aluno, url)

    total_paginas = math.ceil(len(flat_list) / fotos_por_pagina)
    pagina = st.session_state.get("pagina", 0)

    # ====================
    # Navegação com botões
    # ====================
    col_nav1, col_nav2, col_nav3 = st.columns([1,2,1])
    with col_nav1:
        if st.button("⬅ Anterior") and pagina > 0:
            st.session_state["pagina"] = pagina - 1
            st.rerun()
    with col_nav2:
        st.markdown(f"**Página {pagina+1}/{total_paginas} | Fotos {pagina*fotos_por_pagina+1} a {min((pagina+1)*fotos_por_pagina, len(flat_list))} de {len(flat_list)}**", unsafe_allow_html=True)
    with col_nav3:
        if st.button("Próximo ➡") and pagina < total_paginas - 1:
            st.session_state["pagina"] = pagina + 1
            st.rerun()

    # ====================
    # Limpa cache da página anterior
    # ====================
    st.session_state["analise_cache"] = {}

    # Seleciona fotos da página
    start_idx = pagina * fotos_por_pagina
    end_idx = start_idx + fotos_por_pagina
    pagina_atual = flat_list[start_idx:end_idx]

    # Agrupa por aluno
    pagina_alunos = {}
    for escola, aluno, foto in pagina_atual:
        pagina_alunos.setdefault((escola, aluno), []).append(foto)

    # Barra de progresso
    progress_bar = st.progress(0, text="Processando imagens...")

    for idx, ((escola, aluno), fotos) in enumerate(pagina_alunos.items(), start=1):
        with st.expander(f"{escola} - {aluno}"):
            for j, file_name in enumerate(fotos, start=1):
                chave_cache = f"{escola}_{aluno}_{file_name}"

                # Baixar imagem
                try:
                    img_bytes = baixar_imagem_gcs(bucket_name, file_name)
                except Exception as e:
                    logging.error(f"Erro ao baixar {file_name}: {e}")
                    continue

                # Analisar DeepFace
                try:
                    resultados, img = analisar_emocao(img_bytes)
                    emocao_dominante = resultados[0]['dominant_emotion']
                    emocao_dominante_pt = traducoes_emocoes.get(emocao_dominante, "Desconhecida")
                except ValueError:
                    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                    resultados = None
                    emocao_dominante_pt = "Sem rosto detectado"
                except Exception as e:
                    logging.error(f"Erro DeepFace {file_name}: {e}")
                    continue

                # Desenha bounding box
                img_bgr_com_bbox = desenhar_bbox(img, resultados)

                # Prepara gráfico
                if resultados:
                    emocoes = resultados[0]['emotion']
                    valores = [float(v) for v in emocoes.values()]
                    labels = [traducoes_emocoes[e] for e in emocoes.keys()]

                    fig, ax = plt.subplots(figsize=(6,4))
                    cores = ["#E53935","#8E24AA","#3949AB","#43A047","#FB8C00","#FDD835","#546E7A"]
                    barras = ax.barh(labels, valores, color=cores)
                    ax.set_xlabel("Probabilidade (%)")
                    ax.set_title("Distribuição das Emoções")
                    ax.invert_yaxis()
                    for bar in barras:
                        width = bar.get_width()
                        ax.text(width+1, bar.get_y()+bar.get_height()/2, f"{width:.1f}%", va='center')
                    fig.tight_layout()

                    col1, col2 = st.columns([1,1])
                    with col1:
                        st.image(cv2.cvtColor(img_bgr_com_bbox, cv2.COLOR_BGR2RGB), caption=f"Foto {j}")
                    with col2:
                        st.success(f"📸 Emoção predominante: {emocao_dominante_pt}")
                        st.pyplot(fig)
                        plt.close(fig)
                else:
                    st.image(cv2.cvtColor(img_bgr_com_bbox, cv2.COLOR_BGR2RGB), caption=f"Foto {j}")
                    st.error("Nenhum rosto detectado.")

        progress_bar.progress(idx / len(pagina_alunos), text=f"Processando {idx}/{len(pagina_alunos)} alunos...")

    progress_bar.empty()

