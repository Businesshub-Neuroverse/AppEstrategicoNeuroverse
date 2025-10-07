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
import gc

# --------------------------------
# Funções auxiliares (sem cache)
# --------------------------------

def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    client = storage.Client()  # espera GOOGLE_APPLICATION_CREDENTIALS no ambiente
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

# --------------------------------
# Função principal
# --------------------------------

def analiseDeSentimentos(email_hash=None):

    # Página / estilo
    st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important; margin-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🧠 Análise de Sentimentos dos Alunos")

    # Consulta (igual ao seu)
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

    traducoes_emocoes = {
        "angry": "Raiva",
        "disgust": "Aborrecida",
        "fear": "Medo",
        "happy": "Alegria",
        "sad": "Tristeza",
        "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    # explode urls
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    resultados_por_aluno = {}
    bucket_name = "littera_images"

    total = len(df_explodido)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, (_, row) in enumerate(df_explodido.iterrows(), start=1):
        aluno = row["aluno_nome"]
        escola = row["escola_nome"]
        file_name = row["url_imagem"]

        img_bytes = None
        resultados = None
        img = None
        emocao_dominante_pt = "Erro"

        # baixar
        try:
            img_bytes = baixar_imagem_gcs(bucket_name, file_name)
        except Exception as e:
            logging.error(f"Erro ao baixar imagem {file_name}: {e}")
            continue

        # analisar
        try:
            resultados, img = analisar_emocao(img_bytes)
            # se resultados OK
            if resultados and len(resultados) > 0:
                dominant = resultados[0].get('dominant_emotion')
                if dominant in traducoes_emocoes:
                    emocao_dominante_pt = traducoes_emocoes[dominant]
                else:
                    emocao_dominante_pt = str(dominant)
            else:
                emocao_dominante_pt = "Sem rosto detectado"
                resultados = None
        except ValueError:
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            emocao_dominante_pt = "Sem rosto detectado"
            resultados = None
        except Exception as e:
            logging.error(f"Erro ao analisar emoção da imagem {file_name}: {e}")
            continue

        resultados_por_aluno.setdefault((escola, aluno), []).append({
            "arquivo": file_name,
            "emocao": emocao_dominante_pt,
            "detalhe": resultados,
            "imagem": img
        })

        progress_bar.progress(i / total)
        status_text.text(f"Analisando {i}/{total}: {file_name}")

    progress_bar.empty()
    status_text.empty()
    gc.collect()

    # Exibição por aluno (mantendo expander)
    for (escola, aluno), fotos in resultados_por_aluno.items():
        resumo_emocoes = " | ".join([foto["emocao"] for foto in fotos])
        with st.expander(f"{escola} - {aluno} - {resumo_emocoes}"):
            for j, foto in enumerate(fotos, start=1):
                try:
                    # caso sem rosto
                    if foto["detalhe"] is None:
                        st.error(f"📸 Foto {j}: Nenhum rosto detectado.")
                        try:
                            st.image(cv2.cvtColor(foto["imagem"], cv2.COLOR_BGR2RGB), caption=f"Foto {j}", use_container_width=True)
                        except Exception as e_img:
                            logging.warning(f"Não foi possível exibir imagem bruta da Foto {j}: {e_img}")
                        continue

                    resultados = foto["detalhe"]
                    img_bgr_com_bbox = foto["imagem"].copy()

                    # desenha bbox com checagem / clipping
                    h_img, w_img = img_bgr_com_bbox.shape[:2]
                    for face in resultados:
                        region = face.get('region', {})
                        if all(k in region for k in ('x', 'y', 'w', 'h')):
                            x = int(region['x']); y = int(region['y']); w = int(region['w']); h = int(region['h'])
                            # Clip para dentro da imagem
                            x = max(0, min(x, w_img-1))
                            y = max(0, min(y, h_img-1))
                            w = max(0, min(w, w_img - x))
                            h = max(0, min(h, h_img - y))
                            if w > 0 and h > 0:
                                cv2.rectangle(img_bgr_com_bbox, (x, y), (x + w, y + h), (0, 255, 0), 2)

                    # converte para RGB para exibição
                    try:
                        img_rgb = cv2.cvtColor(img_bgr_com_bbox, cv2.COLOR_BGR2RGB)
                    except Exception as e_conv:
                        logging.error(f"Erro conversão BGR->RGB foto {j}: {e_conv}")
                        img_rgb = img_bgr_com_bbox  # tenta exibir mesmo assim

                    # pega emoções e converte para floats puros
                    emocoes_raw = resultados[0].get('emotion', {})
                    emocoes = {}
                    for k, v in emocoes_raw.items():
                        try:
                            val = float(v)
                        except Exception:
                            # tenta extrair se for string "np.float32(...)" ou similar
                            try:
                                val = float(str(v).replace("np.float32(", "").replace(")", ""))
                            except Exception:
                                val = 0.0
                        emocoes[k] = val

                    # Se os valores parecem estar na escala [0,1], transforma para % (0-100)
                    max_val = max(emocoes.values()) if len(emocoes) else 0
                    if max_val <= 1.0:
                        emocoes = {k: v * 100.0 for k, v in emocoes.items()}

                    # debug opcional (comente depois)
                    # st.write("DEBUG emoções (float %):", emocoes)

                    valores = [emocoes[k] for k in ['angry','disgust','fear','happy','sad','surprise','neutral'] if k in emocoes]
                    labels = [traducoes_emocoes[k] for k in ['angry','disgust','fear','happy','sad','surprise','neutral'] if k in emocoes]

                    # cria figura
                    try:
                        fig, ax = plt.subplots(figsize=(6, 4))
                        cores = [
                            "#E53935", "#8E24AA", "#3949AB",
                            "#43A047", "#FB8C00", "#FDD835", "#546E7A"
                        ]
                        barras = ax.barh(labels, valores, color=cores[:len(labels)])
                        ax.set_xlabel("Probabilidade (%)")
                        ax.set_title("Distribuição das Emoções (Face Principal)")
                        ax.invert_yaxis()
                        for bar in barras:
                            width = bar.get_width()
                            ax.text(width + 1, bar.get_y() + bar.get_height() / 2, f"{width:.1f}%", va='center')
                        fig.tight_layout()
                    except Exception as e_fig:
                        logging.error(f"Erro ao criar figura da foto {j}: {e_fig}")
                        fig = None

                    # Exibe imagem e gráfico em blocos separados com try/except
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        try:
                            st.image(img_rgb, caption=f"Foto {j}", use_container_width=True)
                        except Exception as e_img_display:
                            logging.error(f"Erro ao exibir imagem da foto {j}: {e_img_display}")
                            st.warning("Não foi possível exibir a imagem.")

                    with col2:
                        st.success(f"📸 Foto {j} - Emoção Predominante: {foto['emocao']}")
                        if fig is not None:
                            try:
                                st.pyplot(fig)
                            except Exception as e_plot:
                                logging.error(f"Erro ao exibir gráfico da foto {j}: {e_plot}")
                                st.warning("Não foi possível exibir o gráfico.")
                            finally:
                                plt.close(fig)
                                gc.collect()

                except Exception as e:
                    logging.error(f"Erro ao exibir item (aluno {aluno} - foto {j}): {e}")
                    st.error(f"Erro ao renderizar foto {j}.")
