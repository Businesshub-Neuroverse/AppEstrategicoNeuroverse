import streamlit as st
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from config import executar_query
from sqlalchemy.exc import OperationalError
import logging

# ===========================
# Função Principal ajustada
# ===========================
def analiseDeSentimentos(email_hash=None):

    # -------------------------
    # CSS e configuração da página
    # -------------------------
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important; margin-top: 0 !important;
    }
    .card { padding: 2px; border-radius: 14px; background-color: #F6F7FF; text-align: center;
           border-left: 6px solid #5A6ACF; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    .card h3 { margin: 0; line-height: 1; font-size: 22px; color: #5A6ACF; }
    .card p { margin: 0; line-height: 1; font-size: 22px; font-weight: bold; color: #333; }
    .card-mini { padding: 8px 14px; font-size: 17px; background: #F6F7FF; border-left: 6px solid #5A6ACF;
                 border-radius: 12px; text-align: center; margin-bottom: 10px; font-weight: 600;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    
    /* -----------------------------
    MULTISELECT / SELECT – ESTILO BASE
    ----------------------------- */

    /* Caixa geral */
    div[data-baseweb="select"] {
        border-radius: 12px !important;
        border: 1px solid #d5d5d5 !important;
        padding: 4px !important;
        background-color: #ffffff !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    /* Foco */
    div[data-baseweb="select"]:focus-within {
        border-color: #5A6ACF !important;
        box-shadow: 0 0 0 2px rgba(90, 106, 207, 0.25) !important;
    }

    /* Texto */
    div[data-baseweb="select"] div {
        font-size: 15px !important;
        color: #333 !important;
    }

    /* Hover no item da lista */
    ul[role="listbox"] > li:hover {
        background-color: #eef0ff !important;
        color: #5A6ACF !important;
        cursor: pointer !important;
    }


    /* -----------------------------
    FIX DEFINITIVO DO FUNDO PRETO
    (Chips + item selecionado)
    ----------------------------- */

    /* Chip do multiselect */
    div[data-baseweb="tag"][class] {
        background: #EEF0FF !important;
        background-color: #EEF0FF !important;
        color: #5A6ACF !important;
        border-radius: 10px !important;
        padding: 2px 8px !important;
    }

    /* Texto do chip */
    div[data-baseweb="tag"][class] span {
        color: #5A6ACF !important;
        font-weight: 600 !important;
    }

    /* Ícone X do chip */
    div[data-baseweb="tag"][class] svg {
        fill: #5A6ACF !important;
    }

    /* Item selecionado na lista */
    ul[role="listbox"] > li[aria-selected="true"] {
        background: #5A6ACF !important;
        color: white !important;
    }
                
    </style>
    """, unsafe_allow_html=True)

    st.set_page_config(page_title="Face Neuro", page_icon="🧠", layout="wide")
    st.markdown("<h2 style='color: #5A6ACF;'>🧠 Análise de Sentimentos dos Alunos nas Ilhas do Conhecimento</h2>", unsafe_allow_html=True)

    if email_hash is None:
        st.warning("Email hash não fornecido.")
        return

    # -------------------------
    # Dicionários de tradução e cores
    # -------------------------
    traducoes_emocoes = {
        "angry": "Raiva",
        "disgust": "Aborrecida",
        "fear": "Medo",
        "happy": "Alegria",
        "sad": "Tristeza",
        "surprise": "Surpresa",
        "neutral": "Neutra"
    }

    cores_emocoes = {
        "Raiva": "#E74C3C",
        "Aborrecida": "#8E44AD",
        "Medo": "#2C3E50",
        "Alegria": "#F1C40F",
        "Tristeza": "#3498DB",
        "Surpresa": "#1ABC9C",
        "Neutra": "#95A5A6"
    }

    # Ordem consistente de emoções (inglês keys)
    ordem_emocoes_eng = ["happy", "sad", "neutral", "angry", "disgust", "fear", "surprise"]

    # -------------------------
    # Buscar dados SQL
    # -------------------------
    query = """
    SELECT 
        s.name AS escola_nome,
        t.education_level AS turma_nivel,
        t.shift AS turma_turno,
        t.grade AS turma_serie,
        t.name AS turma_nome,
        t.year AS turma_ano,
        a.name AS aluno_nome,
        av.status AS avaliacao_status,
        av.feelings_results AS emocoes_imagens
    FROM auth.users u
    JOIN auth.school_users su ON u.id = su.user_id
    JOIN core.schools s ON su.school_id = s.id
    JOIN core.school_classes t ON s.id = t.school_id
    JOIN core.children a ON t.id = a.class_id
    JOIN littera.children_avaliation av ON a.id = av.child_id
    WHERE av.status = 'Concluido' AND av.feelings_results IS NOT NULL
    AND u.email_hash = :email_hash
    ORDER BY t.grade;
    """
    try:
        df = executar_query(query, {"email_hash": email_hash})
    except Exception as e:
        logging.exception("Erro ao executar query:")
        st.error("Erro ao buscar dados.")
        return

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        return

    # -------------------------
    # Criar identificador único da turma
    # -------------------------
    df["turma_id"] = (
        df["turma_ano"].astype(str) + ": " +
        df["turma_serie"].astype(str) + "ª série " +
        df["turma_nome"].astype(str) + " – " +
        df["turma_turno"].astype(str)
    )

    # -------------------------
    # SELECTBOX centralizado para turma e aluno
    # -------------------------
    turmas = sorted(df["turma_id"].unique())
    colA, colB = st.columns(2)

    #c1, c2, c3 = st.columns([1, 2, 1])
    with colA:

        st.markdown("<h3 style='margin-top:18px;'>⬇️ Seleciona a Turma e Aluno abaixo</h3>", unsafe_allow_html=True)

        turma_selecionada = st.selectbox("Selecione uma turma:", turmas)

    df_turma = df[df["turma_id"] == turma_selecionada]
    if df_turma.empty:
        st.warning("Nenhum dado para a turma selecionada.")
        return

    alunos = sorted(df_turma["aluno_nome"].unique())
    with colA:
        aluno_escolhido = st.selectbox("Escolha um aluno:", alunos)

    df_aluno = df_turma[df_turma["aluno_nome"] == aluno_escolhido]
    if df_aluno.empty:
        st.warning("Nenhum dado para o aluno selecionado.")
        return

    # -------------------------
    # Preparar todas as fotos da turma (para média)
    # -------------------------
    fotos_da_turma = []   # lista de dicts {'emotions': {...}, 'primary_emotion': ...}

    for idx, item in enumerate(df_turma["emocoes_imagens"]):
        if item is None:
            continue
        # item pode ser list (já desserializado) ou string JSON
        try:
            if isinstance(item, list):
                fotos_list = item
            elif isinstance(item, str):
                fotos_list = json.loads(item)
            else:
                # formato inesperado: pula
                continue
        except Exception:
            continue

        # fotos_list deve ser uma lista de objetos
        if not isinstance(fotos_list, list):
            continue

        for foto in fotos_list:
            # validações
            if not isinstance(foto, dict):
                continue
            if "emotions" not in foto or foto["emotions"] is None:
                continue
            # garante estrutura correta: emotions é dict
            if not isinstance(foto["emotions"], dict):
                continue
            fotos_da_turma.append(foto)

    # -------------------------
    # Calcular média por emoção (turma) — usa apenas fotos válidas
    # -------------------------
    media_turma = None
    if len(fotos_da_turma) > 0:
        soma = {k: 0.0 for k in ordem_emocoes_eng}
        count = 0
        for foto in fotos_da_turma:
            emotions = foto["emotions"]
            # some apenas as keys que existem
            for eng in ordem_emocoes_eng:
                val = emotions.get(eng)
                if val is None:
                    # se não existir, soma 0
                    continue
                # assumindo que os valores do DB já são percentuais (ex: 27.93)
                soma[eng] += float(val)
            count += 1
        # média por foto
        media_turma = {eng: (soma[eng] / count) for eng in ordem_emocoes_eng}
    else:
        media_turma = {eng: 0.0 for eng in ordem_emocoes_eng}

    with colB:
    # -------------------------
    # Mostrar gráfico da média da turma
    # -------------------------
        st.markdown("<h3 style='margin-top:18px;'>📈 Média dos Sentimentos da Turma</h3>", unsafe_allow_html=True)

        keys_pt = [traducoes_emocoes[eng] for eng in ordem_emocoes_eng]
        vals_media = [media_turma[eng] for eng in ordem_emocoes_eng]
        cores_media = [cores_emocoes[k] for k in keys_pt]

        fig_media, ax_media = plt.subplots(figsize=(9, 4))
        bars = ax_media.bar(keys_pt, vals_media, color=cores_media)
        ax_media.set_ylim(0, max(vals_media) * 1.25 if max(vals_media) > 0 else 1)
        ax_media.tick_params(axis='x', rotation=35)
        ax_media.set_ylabel("Percentual")

        for bar, v in zip(bars, vals_media):
            ax_media.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{v:.1f}%", ha='center', fontsize=10, fontweight='bold')

        st.pyplot(fig_media)

    # -------------------------
    # Dados do aluno selecionado: extrair lista de fotos (validações)
    # -------------------------
    raw = df_aluno["emocoes_imagens"].iloc[0]
    if raw is None:
        st.warning("Nenhum dado de emoções para o aluno.")
        return

    try:
        photos = raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        st.warning("Formato de emoções inválido.")
        return

    # filtrar fotos válidas
    fotos_validas = []
    for foto in photos:
        if not isinstance(foto, dict):
            continue
        em = foto.get("emotions")
        if not em or not isinstance(em, dict):
            continue
        fotos_validas.append(foto)

    if len(fotos_validas) == 0:
        st.warning("Nenhuma foto com emoções válidas para o aluno.")
        return

    # -------------------------
    # Título aluno + turma
    # -------------------------
    st.markdown(
        f"""
        <h3>📊 Emoções identificadas em:
            <span style='color:#5A6ACF; font-size:22px;'>
                {aluno_escolhido} | {turma_selecionada}
            </span>
        </h3>
        """,
        unsafe_allow_html=True
    )

   # -------------------------
    # Exibição dos gráficos das fotos do aluno
    # Sempre 3 colunas — mesmo com menos fotos
    # -------------------------

    # garantir lista exata de 3 itens
    fotos_para_exibir = []

    for idx in range(3):
        if idx < len(fotos_validas):
            fotos_para_exibir.append(fotos_validas[idx])
        else:
            fotos_para_exibir.append(None)  # posição vazia → exibirá aviso

    cols_fotos = st.columns(3)

    for i in range(3):
        with cols_fotos[i]:

            resultado = fotos_para_exibir[i]

            # -------------------------
            # Validar foto nula / inválida
            # -------------------------
            if resultado is None:
                st.warning(f"⚠️ A análise da Foto {i+1} não retornou dados.")
                continue

            if not isinstance(resultado, dict):
                st.warning(f"⚠️ A análise da Foto {i+1} retornou um formato inesperado.")
                continue

            if "emotions" not in resultado or resultado["emotions"] is None:
                st.warning(f"⚠️ Foto {i+1} não possui campo 'emotions'.")
                continue

            emotions = resultado["emotions"]

            if not isinstance(emotions, dict):
                st.warning(f"⚠️ Emoções da Foto {i+1} estão em formato inválido.")
                continue

            # -------------------------
            # Emoção predominante
            # -------------------------
            try:
                eng_pred = max(emotions, key=emotions.get)
                pred_pt = traducoes_emocoes.get(eng_pred, eng_pred)
            except Exception:
                pred_pt = "Desconhecida"

            cor_pred = cores_emocoes.get(pred_pt, "#5A6ACF")

            # Mini-card centrado
            st.markdown(
                f"""
                <div style="text-align:center;">
                    <div style="display:inline-block; background:#F6F7FF; padding:8px 12px;
                                border-left:6px solid {cor_pred};
                                border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,0.08);
                                font-weight:600; margin-bottom:6px;">
                        Foto {i+1} — Emoção Predominante: {pred_pt}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # -------------------------
            # Preparar gráfico
            # -------------------------
            labels_pt = []
            valores = []
            cores_graf = []

            for eng in ordem_emocoes_eng:
                if eng in emotions:
                    labels_pt.append(traducoes_emocoes[eng])
                    valores.append(float(emotions[eng]))
                    cores_graf.append(cores_emocoes[traducoes_emocoes[eng]])

            # Gráfico
            fig, ax = plt.subplots(figsize=(4.5, 3.5))
            bars = ax.bar(labels_pt, valores, color=cores_graf)
            ax.set_ylim(0, max(valores) * 1.25 if max(valores) > 0 else 1)
            ax.tick_params(axis='x', rotation=35)
            ax.set_ylabel("Percentual")

            for bar, v in zip(bars, valores):
                ax.text(
                    bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f"{v:.1f}%",
                    ha='center',
                    fontsize=10,
                    fontweight='bold'
                )

            st.pyplot(fig)
