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
# Funções auxiliares
# ================================
def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    #client = storage.Client.from_service_account_json("chave_gcp.json")
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
        detector_backend="opencv", # mtcnn, opencv
        enforce_detection=True
    )
    if isinstance(resultados, dict):
        resultados = [resultados]
    return resultados, img

# ================================
# Função principal
# ================================
def analiseDeSentimentos(email_hash=None):

    # ================================
    # Configurações da página
    # ================================
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important; margin-top: 0 !important;
    }
    .stTextInput > div > div > input {
        border: 2px solid #4CAF50; border-radius: 8px; padding: 8px; outline: none;
    }
    .stTextInput > div > div > input:focus {
        border: 2px solid #2196F3; box-shadow: 0 0 5px rgba(33,150,243,0.5);
    }
    </style>
    """, unsafe_allow_html=True)

    st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
    st.title("🧠 Análise de Sentimentos dos Alunos")

    if email_hash is None:
        st.warning("Email hash não fornecido.")
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

    # Consulta SQL
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
    WHERE av.status = 'Concluido' 
      AND av.feelings_urls IS NOT NULL  
      AND u.email_hash = :email_hash
    ORDER BY av.classification_score
    """)

    try:
        df = pd.read_sql(query, engine, params={"email_hash": email_hash})
    except OperationalError as e:
        logging.error(f"Falha ao conectar banco: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        return
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        st.error("Ocorreu um erro inesperado.")
        return

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        return

    # Explode URLs
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    # Agrupa fotos por aluno
    alunos_dict = {}
    for _, row in df_explodido.iterrows():
        chave = (row["escola_nome"], row["aluno_nome"])
        alunos_dict.setdefault(chave, []).append(row["url_imagem"])

    bucket_name = "littera_images"

    # ================================
    # Exibição dos alunos
    # ================================
    for (escola, aluno), fotos in alunos_dict.items():
        with st.expander(f"{escola} - {aluno}", expanded=False):
            with st.form(key=f"form_{aluno}"):
                submit_btn = st.form_submit_button(f"Analisar {aluno}")
                if submit_btn:
                    barra_aluno = st.progress(0, text=f"Processando {aluno}...")

                    # Processar de 3 em 3 imagens
                    for i in range(0, len(fotos), 3):
                        subset = fotos[i:i+3]
                        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
                        fig.subplots_adjust(hspace=0.2)

                        for j, foto in enumerate(subset):
                            idx = i + j + 1
                            try:
                                img_bytes = baixar_imagem_gcs(bucket_name, foto)
                                resultados, img = analisar_emocao(img_bytes)

                                # Recorte simples do bounding box
                                region = resultados[0].get('region', {})
                                if all(k in region for k in ['x','y','w','h']):
                                    x, y, w, h = region['x'], region['y'], region['w'], region['h']
                                    rosto = img[y:y+h, x:x+w]

                                    if rosto.size == 0:
                                        st.warning(f"Foto: {idx}: Sem rosto detectado")
                                        continue

                                    imagem_red = cv2.resize(rosto, (200, 200))
                                    img_rgb = cv2.cvtColor(imagem_red, cv2.COLOR_BGR2RGB)

                                    # Linha 1 → imagem e emoção predominante
                                    ax_img = axes[0, j]
                                    ax_img.imshow(img_rgb)
                                    ax_img.axis("off")
                                    ax_img.text(0.5, -0.1, f"Foto {idx}", fontsize=10, ha="center", va="top", transform=ax_img.transAxes)

                                    emocao_dominante = max(resultados[0]['emotion'], key=resultados[0]['emotion'].get)
                                    ax_img.set_title(f"Emoção predominante: {traducoes_emocoes[emocao_dominante]}", fontsize=10, color="blue", pad=7)

                                    # Linha 2 → gráfico de barras verticais
                                    ax_graph = axes[1, j]
                                    emocoes = resultados[0]['emotion']
                                    labels = [traducoes_emocoes[e] for e in emocoes.keys()]
                                    valores = list(emocoes.values())
                                    cores = ["#E53935","#8E24AA","#3949AB","#43A047","#FB8C00","#FDD835","#546E7A"]

                                    bars = ax_graph.bar(labels, valores, color=cores)
                                    ax_graph.set_ylim(0, 110)
                                    ax_graph.set_ylabel("%")

                                    # Adiciona os valores acima das barras
                                    for bar in bars:
                                        ax_graph.text(
                                            bar.get_x() + bar.get_width()/2, 
                                            bar.get_height() + 1,
                                            f"{bar.get_height():.1f}%",
                                            ha='center', va='bottom', fontsize=9
                                        )

                                    ax_graph.set_xticklabels(labels, rotation=45, ha="right")

                                else:
                                    st.warning(f"Foto {idx}: Sem rosto detectado")

                            except ValueError:
                                st.warning(f"Foto {idx}: Sem rosto detectado")
                            except Exception as e:
                                st.warning(f"Foto {idx}: Sem rosto detectado ({e})")

                            barra_aluno.progress(idx / len(fotos), text=f"Processando {idx}/{len(fotos)} fotos...")

                        # Remove eixos vazios se não houver 3 imagens
                        for k in range(len(subset), 3):
                            axes[0, k].axis("off")
                            axes[1, k].axis("off")

                        st.pyplot(fig)
                        plt.close(fig)

                    barra_aluno.empty()


