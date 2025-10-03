import streamlit as st
import pandas as pd
import cv2
from google.cloud import storage
from deepface import DeepFace
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import text
from config import engine
from sqlalchemy.exc import OperationalError
import logging
st.write("fez todos os imports")

def analiseDeSentimentos(email_hash=None):
    st.write("entrou no sentimento")
    # ================================
    # 🎨 Estilo da página
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

    # ---------------------------
    # Consulta SQL
    # ---------------------------
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

    # ================================
    # Traduções de emoções
    # ================================
    traducoes_emocoes = {
        "angry": "Raiva",
        "disgust": "Aborrecida",
        "fear": "Medo",
        "happy": "Alegria",
        "sad": "Tristeza",
        "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    # ================================
    # Autenticação Google Cloud
    # ================================
    client = storage.Client.from_service_account_json("chave_gcp.json")
    #st.dataframe(df)
    # ================================
    # Quebra imagens em várias linhas
    # ================================
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split")
    df_explodido = df_explodido.rename(columns={"urls_imagens_split": "url_imagem"})
    #st.dataframe("df explodido", df_explodido)
    # ================================
    # Processa imagens com DeepFace
    # ================================
    resultados_por_aluno = {}

    for _, row in df_explodido.iterrows():
        bucket_name = "littera_images"
        aluno = row["aluno_nome"]
        escola = row["escola_nome"]
        file_name = row["url_imagem"]

        # Baixa imagem
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        img_bytes = blob.download_as_bytes()

        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        try:
            resultados = DeepFace.analyze(
                img,
                actions=['emotion'],
                detector_backend="mtcnn",
                enforce_detection=True
            )

            if isinstance(resultados, dict):
                resultados = [resultados]

            emocao_dominante = resultados[0]['dominant_emotion']
            emocao_dominante_pt = traducoes_emocoes[emocao_dominante]

            if (escola, aluno) not in resultados_por_aluno:
                resultados_por_aluno[(escola, aluno)] = []

            resultados_por_aluno[(escola, aluno)].append({
                "arquivo": file_name,
                "emocao": emocao_dominante_pt,
                "detalhe": resultados,
                "imagem": img
            })

        except ValueError:
            if (escola, aluno) not in resultados_por_aluno:
                resultados_por_aluno[(escola, aluno)] = []
            resultados_por_aluno[(escola, aluno)].append({
                "arquivo": file_name,
                "emocao": "Sem rosto detectado",
                "detalhe": None,
                "imagem": img
            })

    # ================================
    # Expansores por aluno com resumo das 3 emoções
    # ================================
    for (escola, aluno), fotos in resultados_por_aluno.items():
        resumo_emocoes = " | ".join([foto["emocao"] for foto in fotos])
        
        with st.expander(f"{escola} - {aluno} - {resumo_emocoes}"):
            for i, foto in enumerate(fotos, start=1):
                

                if foto["detalhe"] is None:
                    st.error("Nenhum rosto detectado nesta foto.")
                    continue

                resultados = foto["detalhe"]
                img_bgr_com_bbox = foto["imagem"].copy()

                # desenha bounding box
                for face in resultados:
                    region = face['region']
                    x, y, w, h = region['x'], region['y'], region['w'], region['h']
                    cv2.rectangle(img_bgr_com_bbox, (x, y), (x + w, y + h), (0, 255, 0), 2)

                img_rgb = cv2.cvtColor(img_bgr_com_bbox, cv2.COLOR_BGR2RGB)

                # gráfico emoções
                emocoes = resultados[0]['emotion']
                x_vals = list(emocoes.values())
                y_labels = [traducoes_emocoes[e] for e in emocoes.keys()]

                fig, ax = plt.subplots(figsize=(6, 4))
                cores = ["#DD0707", "#4C0BC5", '#F3EF04', "#03860E", '#D66214', "#F30454", '#99FF99']
                bars = ax.barh(y_labels, x_vals, color=cores)
                ax.set_xlabel("Probabilidade (%)")
                ax.set_title("Distribuição das Emoções (Face Principal)")
                ax.bar_label(bars, fmt='%.1f%%', padding=3)

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(img_rgb, caption=f"Foto {i}")
                with col2:
                    st.success(f"📸 Foto {i} - Emoção Predominante: {foto['emocao']}")
                    st.pyplot(fig)



