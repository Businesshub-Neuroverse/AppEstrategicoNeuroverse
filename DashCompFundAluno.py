# ---------------------------
# Bibliotecas
# ---------------------------
import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from sqlalchemy.exc import OperationalError
from config import executar_query
import logging

# ---------------------------
# Funções auxiliares
# ---------------------------

def aplicar_css_tema_claro():
    """Aplica todo o CSS do tema claro do dashboard."""
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display:none !important; }

    body, .stApp, [data-testid="stAppViewContainer"],
    .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
        background-color: #ffffff !important;
    }

    .kpi-card {
        background: #F6F7FF;
        border-left: 6px solid #5A6ACF;
        padding: 10px;
        border-radius: 12px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06);
        text-align: left;
    }
    .kpi-number {
        font-size:28px;
        font-weight:700;
        color:#111827;
    }
    .kpi-label {
        color:#4B5563;
        font-size:13px;
        margin-top:0px;
    }

    /* Select */
    div[data-baseweb="select"] {
        border-radius: 12px !important;
        border: 1px solid #d5d5d5 !important;
        padding: 4px !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="select"]:focus-within {
        border-color: #5A6ACF !important;
        box-shadow: 0 0 0 2px rgba(90,106,207,0.25) !important;
    }

    /* Tags */
    div[data-baseweb="tag"][class] {
        background: #EEF0FF !important;
        color: #5A6ACF !important;
        border-radius: 10px !important;
        padding: 2px 8px !important;
    }
    div[data-baseweb="tag"][class] span {
        color: #5A6ACF !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def classificar(soma_erros):
    """Retorna a classificação baseada na soma de erros."""
    if soma_erros >= 18: return "Grave"
    if soma_erros >= 14: return "Crítico"
    if soma_erros >= 10: return "Regular"
    if soma_erros >= 7: return "Bom"
    if soma_erros >= 4: return "Ótimo"
    return "Excelente"


def criar_html_tabela(df, cores):
    """Gera a tabela HTML colorida (usa cores por classificação)."""
    html = "<table style='border-collapse: collapse; width:100%; font-size:16px;'>"
    html += "<tr>" + "".join(
        f"<th style='border:1px solid #ddd; padding:8px; background:#f2f2f2'>{col}</th>"
        for col in df.columns
    ) + "</tr>"

    for _, row in df.iterrows():
        cor = cores.get(row["Classificação"], "white")
        r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
        texto = "black" if (0.299*r + 0.587*g + 0.114*b) > 186 else "white"

        html += "<tr>" + "".join(
            f"<td style='border:1px solid #ddd; padding:8px; background:{cor}; color:{texto}'>{row[col]}</td>"
            for col in df.columns
        ) + "</tr>"

    html += "</table>"
    return html


# ---------------------------
# FUNÇÃO PRINCIPAL
# ---------------------------
def dashboardCompFund(email_hash=None):

    st.set_page_config(
        page_title="Competências Fundamentais",
        page_icon="assets/favicon.ico",
        layout="wide"
    )

    aplicar_css_tema_claro()

    st.markdown("<h2 style='color:#5A6ACF;'>📊 Desempenho dos Alunos nas Competências Fundamentais</h2>", unsafe_allow_html=True)

    # =============================
    # CONSULTA SQL
    # =============================
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
        av.interpretation_score AS pts_ilha_leitura,
        av.scriptura_score AS pts_ilha_escrita,
        av.calculum_score AS pts_ilha_calculo
    FROM auth.users u
    JOIN auth.school_users su ON u.id = su.user_id
    JOIN core.schools s ON su.school_id = s.id
    JOIN core.school_classes t ON s.id = t.school_id
    JOIN core.children a ON t.id = a.class_id
    JOIN littera.children_avaliation av ON a.id = av.child_id
    WHERE av.status = 'Concluido'
    AND u.email_hash = :email_hash
    ORDER BY t.grade
    """

    try:
        df = executar_query(query, params={"email_hash": email_hash})
    except Exception as e:
        logging.exception("Erro ao consultar base de dados.")
        st.error("Erro ao consultar base de dados.")
        return

    if df is None or df.empty:
        st.warning("Nenhum registro encontrado.")
        return

    # =============================
    # TRATAMENTO DOS DADOS
    # =============================
    df["turma_id"] = (
        df["turma_ano"].astype(str) + ": " +
        df["turma_serie"].astype(str) + "ª série " +
        df["turma_nome"] + " " + df["turma_turno"]
    )

    # garantir colunas numéricas
    for col in ["pts_ilha_leitura", "pts_ilha_escrita", "pts_ilha_calculo"]:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["soma_erros"] = df["pts_ilha_leitura"] + df["pts_ilha_escrita"] + df["pts_ilha_calculo"]

    # =============================
    # FILTRO MULTISELECT
    # =============================
    turmas = sorted(df["turma_id"].unique())
    opcoes = ["Todos"] + turmas
    turma_select = st.multiselect("Selecione uma ou mais turmas:", opcoes, default=["Todos"])

    if not turma_select or "Todos" in turma_select:
        turma_select = ["Todos"]
    else:
        df = df[df["turma_id"].isin(turma_select)]

    # =============================
    # KPIs SUPERIORES
    # =============================
    total_turmas = df["turma_id"].nunique()
    total_alunos = df["aluno_nome"].nunique()
    pct_grave = (df[df["soma_erros"] >= 18]["aluno_nome"].nunique() / total_alunos * 100) if total_alunos else 0

    k1, k2, k3 = st.columns([1,1,1.5])
    kpi_data = [
        ("Turmas", total_turmas, k1),
        ("Alunos", total_alunos, k2),
        ("% Alunos como Grave", f"{pct_grave:.1f}%", k3)
    ]
    for label, value, container in kpi_data:
        if isinstance(value, float):
            display = f"{value:.1f}"
        else:
            display = value
        container.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-number'>{display}</div></div>",
            unsafe_allow_html=True
        )

    # =============================
    # CLASSIFICAÇÃO
    # =============================
    df["Classificação"] = df["soma_erros"].apply(classificar)
    ordem = ["Grave", "Crítico", "Regular", "Bom", "Ótimo", "Excelente"]

    cores_classificacao = {
        "Grave": "#FF3A3A",
        "Crítico": "#FF7E7E",
        "Regular": "#FCA106",
        "Bom": "#FFCD32",
        "Ótimo": "#A3ED97",
        "Excelente": "#5ACF47"
    }

    # Paleta para turmas (escolha elegante e repetível)
    paleta_turmas = px.colors.qualitative.Pastel + px.colors.qualitative.Set2 + px.colors.qualitative.Set3
    turmas_unicas = list(df["turma_id"].unique())
    cores_por_turma = {turma: paleta_turmas[i % len(paleta_turmas)] for i, turma in enumerate(turmas_unicas)}

    # =============================
    # ABAS (5 VISÕES)
    # =============================
    aba1, aba2= st.tabs([
        "📈 Ilhas por Turma e Alunos (Empilhado)", 
        "👥 Relação de Alunos por Classificação",
    ])


    # ========================================================
    # ABA 1 — CLASSIFICAÇÃO POR TURMA (STACKED)
    # ========================================================
    with aba1:
        st.markdown("<h3 style='color:#000'>📚 Distribuição de Classificações por Turma e Alunos</h3>", unsafe_allow_html=True)
        st.caption("Mostrando a proporção de alunos por classificação dentro de cada turma nas ilhas: Leitura, Escrita e Cálculo.")

        # Agrupar dados
        agrupado = df.groupby(["turma_id", "Classificação"]).agg(
            qtd=("aluno_nome", "count")
        ).reset_index()

        # Total de alunos por turma
        totals = agrupado.groupby("turma_id")["qtd"].transform("sum")
        agrupado["percent"] = (agrupado["qtd"] / totals * 100).round(1)

        agrupado["eixo_X"] = agrupado["turma_id"].astype(str) + " - " + totals.astype(str) + " Alunos"


        # Label com alunos + percentual
        agrupado["label"] = agrupado.apply(
            lambda row: f"{row['qtd']} aluno(s) — {row['percent']}%", axis=1
        )

        # Garantir ordem fixa das classificações
        ordem_class = ["Grave", "Crítico", "Regular", "Bom", "Ótimo", "Excelente"]
        agrupado["Classificação"] = pd.Categorical(agrupado["Classificação"], categories=ordem_class, ordered=True)

        # Gráfico de barras empilhadas
        fig1 = px.bar(
            agrupado.sort_values(["turma_id", "Classificação"]),
            x="eixo_X",
            y="percent",
            color="Classificação",
            text="label",
            color_discrete_map=cores_classificacao,
            barmode="stack",
            height=500
        )

        fig1.update_layout(
            xaxis_title="Turmas",
            yaxis_title="Percentual (%)",
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend_title="Classificação"
        )

        fig1.update_traces(
            textposition="inside",
            textfont=dict(size=16),
            insidetextanchor="middle"
        )

        st.plotly_chart(fig1, width='stretch')

    # ========================================================
    # ABA 2 — TABELA (INCLUINDO TURMA)
    # ========================================================
    with aba2:
        st.markdown("<h3 style='color:#000'>📋 Relação de Alunos por Classificação</h3>", unsafe_allow_html=True)

        classific_select = st.selectbox("⬇️Selecione a classificação desejada abaixo⬇️", df["Classificação"].unique())

        df_classific = df[df["Classificação"] == classific_select]

        df_tabela = df_classific[[
            "Classificação",
            "soma_erros",
            "pts_ilha_leitura",
            "pts_ilha_escrita",
            "pts_ilha_calculo",
            "aluno_nome",
            "turma_id"
        ]].sort_values(["Classificação", "aluno_nome"]).rename(columns={
            "soma_erros": "Total de Erros",
            "pts_ilha_leitura": "Erros em Leitura",
            "pts_ilha_escrita": "Erros em Escrita",
            "pts_ilha_calculo": "Erros em Cálculo",
            "aluno_nome": "Nome do Aluno(a)",
            "turma_id": "Turma"
        })

        st.markdown(criar_html_tabela(df_tabela, cores_classificacao), unsafe_allow_html=True)

    # FIM da função dashboard
