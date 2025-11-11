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

# ------------------------
# Função para detectar o maior rosto (usa MTCNN e fallback)
# ------------------------
def detectar_maior_rosto_com_fallback(img, detector_backend="mtcnn"):
    """
    Recebe imagem BGR (numpy.ndarray).
    Primeiro tenta MTCNN (recomendado). Se falhar, tenta DeepFace.extract_faces como fallback.
    Retorna dicionário com 'facial_area': {'x','y','w','h'} ou None.
    """
    # 1) Tentar MTCNN
    try:
        from mtcnn import MTCNN
        detector = MTCNN()
        # MTCNN espera RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        dets = detector.detect_faces(rgb)
        faces = []
        for d in dets:
            box = d.get("box", None)
            conf = d.get("confidence", 0)
            if box is None:
                continue
            x, y, w, h = box
            # normalizar valores negativos e inteiros
            x = int(max(0, x))
            y = int(max(0, y))
            w = int(max(0, w))
            h = int(max(0, h))
            faces.append({"facial_area": {"x": x, "y": y, "w": w, "h": h}, "confidence": conf})
        if faces:
            maior = max(faces, key=lambda r: r["facial_area"]["w"] * r["facial_area"]["h"])
            return maior
    except Exception:
        # falha no MTCNN (ex.: não instalado) → segue para fallback
        pass

    # 2) Fallback: DeepFace.extract_faces
    try:
        detections = DeepFace.extract_faces(img_path=img, detector_backend=detector_backend, enforce_detection=False)
        if detections:
            # extract_faces retorna lista de dict com 'facial_area' chave
            maior = max(detections, key=lambda r: r["facial_area"]["w"] * r["facial_area"]["h"] if r.get("facial_area") else 0)
            return maior
    except Exception:
        pass

    return None


# ================================
# Baixar imagem do GCS
# ================================
def baixar_imagem_gcs(bucket_name: str, file_name: str) -> bytes:
    #client = storage.Client.from_service_account_json("chave_gcp.json")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    return blob.download_as_bytes()


# ================================
# Analisa apenas o rosto principal
# ================================
def analisar_emocao(img_bytes: bytes, detector_backend="mtcnn"):
    """
    Detecta o maior rosto e analisa somente esse recorte.
    Retorna: resultado_lista, imagem_original (BGR), bbox (x,y,w,h)
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # detectar maior rosto
    maior = detectar_maior_rosto_com_fallback(img, detector_backend=detector_backend)
    if maior is None:
        raise ValueError("Nenhum rosto detectado")

    fa = maior.get("facial_area")
    if not fa or not all(k in fa for k in ("x", "y", "w", "h")):
        raise ValueError("Bounding box inválido")

    # garantir inteiros e limites dentro da imagem
    h_img, w_img = img.shape[:2]
    x = int(max(0, fa["x"]))
    y = int(max(0, fa["y"]))
    w = int(max(0, fa["w"]))
    h = int(max(0, fa["h"]))

    # ajustar se exceder limites
    x2 = min(w_img, x + w)
    y2 = min(h_img, y + h)
    w = x2 - x
    h = y2 - y
    if w <= 0 or h <= 0:
        raise ValueError("Rosto fora dos limites da imagem")

    rosto = img[y:y+h, x:x+w]

    if rosto.size == 0:
        raise ValueError("Rosto recortado vazio")

    # Analisa apenas o recorte (usa enforce_detection=False para evitar crash)
    resultado = DeepFace.analyze(
        rosto,
        actions=["emotion"],
        detector_backend=detector_backend,
        enforce_detection=False
    )

    # padroniza saída para lista
    if isinstance(resultado, dict):
        resultado = [resultado]

    return resultado, img, (x, y, w, h)


# ================================
# Função principal Streamlit
# ================================
def analiseDeSentimentos(email_hash=None):
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

    # Explode URLs e agrupa por aluno
    df["urls_imagens_split"] = df["urls_imagens"].str.split(";")
    df_explodido = df.explode("urls_imagens_split").rename(columns={"urls_imagens_split": "url_imagem"})

    alunos_dict = {}
    for _, row in df_explodido.iterrows():
        chave = (row["escola_nome"], row["aluno_nome"])
        alunos_dict.setdefault(chave, []).append(row["url_imagem"])

    bucket_name = "littera_images"

    # Loop por aluno
    for (escola, aluno), fotos in alunos_dict.items():
        with st.expander(f"{escola} - {aluno}", expanded=False):
            with st.form(key=f"form_{aluno}"):
                submit_btn = st.form_submit_button(f"Analisar {aluno}")
                if not submit_btn:
                    continue

                barra_aluno = st.progress(0, text=f"Processando {aluno}...")

                # processa em blocos de 3
                for i in range(0, len(fotos), 3):
                    subset = fotos[i:i+3]
                    # garantir axes sempre 2D (squeeze=False)
                    fig, axes = plt.subplots(2, 3, figsize=(14, 8), squeeze=False)
                    fig.subplots_adjust(hspace=0.18, wspace=0.25)

                    for j, foto in enumerate(subset):
                        idx = i + j + 1
                        try:
                            img_bytes = baixar_imagem_gcs(bucket_name, foto)
                            resultados, img, (x, y, w, h) = analisar_emocao(img_bytes, detector_backend="mtcnn")

                            # mostra apenas o rosto usado na análise (garante mesma imagem)
                            rosto = img[y:y+h, x:x+w]
                            if rosto.size == 0:
                                st.warning(f"Foto {idx}: Sem rosto detectado")
                                continue

                            imagem_red = cv2.resize(rosto, (200, 200))
                            img_rgb = cv2.cvtColor(imagem_red, cv2.COLOR_BGR2RGB)

                            # Plot imagem
                            ax_img = axes[0, j]
                            ax_img.imshow(img_rgb)
                            ax_img.axis("off")
                            ax_img.text(0.5, -0.12, f"Foto {idx}", fontsize=10, ha="center", va="top", transform=ax_img.transAxes)

                            emocao_dominante = max(resultados[0]["emotion"], key=resultados[0]["emotion"].get)
                            ax_img.set_title(f"Emoção: {traducoes_emocoes.get(emocao_dominante, emocao_dominante)}",
                                             fontsize=10, color="blue", pad=5)

                            # gráfico de barras vertical
                            ax_graph = axes[1, j]
                            emocoes = resultados[0]["emotion"]
                            labels = [traducoes_emocoes.get(k, k) for k in emocoes.keys()]
                            valores = list(emocoes.values())
                            cores = ["#E53935","#8E24AA","#3949AB","#43A047","#FB8C00","#FDD835","#546E7A"]

                            bars = ax_graph.bar(labels, valores, color=cores)
                            ax_graph.set_ylim(0, 110)
                            ax_graph.set_ylabel("%")
                            ax_graph.set_xticklabels(labels, rotation=45, ha="right")

                            for bar in bars:
                                ax_graph.text(bar.get_x() + bar.get_width()/2,
                                              bar.get_height() + 1,
                                              f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)

                        except ValueError:
                            st.warning(f"Foto {idx}: Sem rosto detectado")
                        except Exception as e:
                            st.warning(f"Foto {idx}: Erro ao processar ({e})")

                        barra_aluno.progress(idx / len(fotos), text=f"Processando {idx}/{len(fotos)} fotos...")

                    # desliga eixos vazios
                    for k in range(len(subset), 3):
                        axes[0, k].axis("off")
                        axes[1, k].axis("off")

                    st.pyplot(fig)
                    plt.close(fig)

                barra_aluno.empty()
