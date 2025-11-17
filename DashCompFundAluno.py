# ---------------------------
# Bibliotecas
# ---------------------------
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import streamlit as st
import numpy as np
from sqlalchemy import text
from config import executar_query
from sqlalchemy.exc import OperationalError
import logging


def dashboardCompFund(email_hash=None):
    """
    Dashboard de Competências Fundamentais:
    - Gráfico de barras horizontais com número de alunos por turma
    - Gráfico de pizza com classificação de erros (ilhas) para a turma clicada
    """

    # ---------------------------
    # Estilo da página
    # ---------------------------
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important; margin-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Configuração básica do Streamlit
    st.set_page_config(
        page_title="Competências Fundamentais",
        page_icon="assets/favicon.ico",
        layout="wide"
    )

    st.markdown(
        "<h2 style='color: #5A6ACF;'>📊 Desempenho dos Alunos nas Competências Fundamentais</h2>",
        unsafe_allow_html=True
    )

    # ---------------------------
    # Consulta SQL
    # ---------------------------
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
    except OperationalError as e:
        logging.error(f"Falha operacional ao conectar banco: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        df = pd.DataFrame()
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        st.error("Ocorreu um erro inesperado. Tente novamente mais tarde.")
        df = pd.DataFrame()

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    # ---------------------------
    # Preparação dos dados para gráfico de barras
    # ---------------------------
    df_stack = df.groupby(
        ["turma_ano", "turma_serie", "turma_nome", "turma_turno"],
        as_index=False
    ).agg(qtd_alunosAvaliados=("aluno_nome", "count"))

    df_stack["eixoY"] = (
        df_stack["turma_ano"].astype(str) + ": " +
        df_stack["turma_serie"].astype(str) + "ª série " +
        df_stack["turma_nome"].astype(str) + " (" +
        df_stack["turma_turno"].astype(str) + ")"
    )

    df_stack["texto_barra"] = df_stack["qtd_alunosAvaliados"].astype(str) + " Alunos"
    df_stack["eixo_XQtd_Alunos"] = df_stack["qtd_alunosAvaliados"].astype(str)

    if df_stack.empty:
        st.warning("Sem dados para montar gráfico.")
        return

    # ---------------------------
    # Layout colunas
    # ---------------------------
    col1, col2 = st.columns(2)

    # ---------------------------
    # Gráfico de barras
    # ---------------------------
    cores_barras = px.colors.qualitative.Vivid

    with col1:
        escola_nome = df["escola_nome"].dropna().unique()
        if len(escola_nome) > 0:
            escola_nome = escola_nome[0]
        else:
            escola_nome = "Escola não identificada"

        st.markdown(
            f"""
            <h4 style='color: #000000;'>🏫 {escola_nome}</h4>
            <p style='font-size:16px; color:#666; margin-top:-10px;'>
            <em>Clique na barra abaixo para selecionar a turma desejada</em>
            </p>
            """,
            unsafe_allow_html=True
        )

        fig_stack = px.bar(
            df_stack,
            x="eixo_XQtd_Alunos",
            y="eixoY",
            color="eixoY",
            color_discrete_sequence=cores_barras,
            text="texto_barra",
            orientation="h",
            labels={
                "eixo_XQtd_Alunos": "Quantidade de Alunos Avaliados",
                "eixoY": "Série do Aluno",
                "texto_barra": ""
            }
        )

        fig_stack.update_layout(
            hovermode="closest",
            showlegend=False,
            paper_bgcolor='white',
            plot_bgcolor="white",
            autosize=True,
            margin=dict(l=210, r=0, t=0, b=80),
            xaxis=dict(title=dict(text="Quantidade de Alunos Avaliados", font=dict(size=16)), tickfont=dict(size=14)),
            yaxis=dict(title=dict(text=""), tickfont=dict(size=14))
        )

        fig_stack.update_traces(textfont=dict(size=14, color="white"), insidetextanchor="middle")

        # Captura clique
        selected_points = plotly_events(fig_stack, select_event=True, key="stack_click")

        # ✅ Seleção automática da primeira turma se nenhuma foi clicada
        if not selected_points and not df_stack.empty:
            selected_points = [{"y": df_stack["eixoY"].iloc[0]}]
            st.caption("🔹 Exibindo automaticamente a primeira turma da lista.")

    # ---------------------------
    # Identifica turma clicada
    # ---------------------------
    ponto = selected_points[0]
    turma_y = ponto.get("y")
    turma_clicada = df_stack.loc[df_stack["eixoY"] == turma_y]

    if turma_clicada.empty:
        st.warning("Não foi possível identificar a turma clicada.")
        return

    turma_ano = turma_clicada["turma_ano"].iloc[0]
    turma_serie = turma_clicada["turma_serie"].iloc[0]
    turma_nome = turma_clicada["turma_nome"].iloc[0]
    turma_turno = turma_clicada["turma_turno"].iloc[0]

    # ---------------------------
    # Filtra alunos da turma clicada
    # ---------------------------
    df_turma = df[
        (df["turma_ano"] == turma_ano) &
        (df["turma_serie"] == turma_serie) &
        (df["turma_nome"] == turma_nome) &
        (df["turma_turno"] == turma_turno)
    ].copy()

    if df_turma.empty:
        st.warning("Não há alunos registrados para a turma selecionada.")
        return

    # ---------------------------
    # Soma dos erros e classificação
    # ---------------------------
    df_turma["pts_ilha_leitura"] = df_turma["pts_ilha_leitura"].fillna(0).astype(int)
    df_turma["pts_ilha_escrita"] = df_turma["pts_ilha_escrita"].fillna(0).astype(int)
    df_turma["pts_ilha_calculo"] = df_turma["pts_ilha_calculo"].fillna(0).astype(int)

    df_turma["soma_erros"] = (
        df_turma["pts_ilha_leitura"] +
        df_turma["pts_ilha_escrita"] +
        df_turma["pts_ilha_calculo"]
    )

    def classificar(soma):
        if soma >= 18:
            return "Grave"
        elif soma >= 14:
            return "Crítico"
        elif soma >= 10:
            return "Regular"
        elif soma >= 7:
            return "Bom"
        elif soma >= 4:
            return "Ótimo"
        else:
            return "Excelente"

    df_turma["classificacao"] = df_turma["soma_erros"].apply(classificar)

    # ---------------------------
    # Pizza
    # ---------------------------
    df_pizza = (
        df_turma.groupby("classificacao", as_index=False)
        .agg(qtd_alunos=("aluno_nome", "count"))
    )

    ordem = ["Grave", "Crítico", "Regular", "Bom", "Ótimo", "Excelente"]
    df_pizza["classificacao"] = pd.Categorical(df_pizza["classificacao"], categories=ordem, ordered=True)
    df_pizza = df_pizza.sort_values("classificacao")

    if df_pizza.empty:
        st.warning("Não foi possível gerar a distribuição para a turma selecionada.")
        return

    intervalos = {
        "Grave": "18 a 21 erros",
        "Crítico": "14 a 17 erros",
        "Regular": "10 a 13 erros",
        "Bom": "7 a 9 erros",
        "Ótimo": "4 a 6 erros",
        "Excelente": "0 a 3 erros"
    }

    df_pizza["legenda"] = df_pizza["classificacao"].map(lambda x: f"{x} ({intervalos.get(x, '')})")

    with col2:
        st.markdown(
            f"""
            <h4 style='color: #000000;'>
                🎯 Classificação — {turma_ano}: {turma_serie}ª série {turma_nome} ({turma_turno})
            </h4>
            <p style='font-size:16px; color:#666; margin-top:-10px;'>
                <em>Avaliação das Ilhas: Leitura, Escrita e Cálculo</em>
            </p>
            """,
            unsafe_allow_html=True
        )

        fig_pizza = px.pie(
            df_pizza,
            names="legenda",
            values="qtd_alunos",
            color="classificacao",
            color_discrete_map={
                "Grave": "#FF3A3A",
                "Crítico": "#FF7E7E",
                "Regular": "#FCA106",
                "Bom": "#FFCD32",
                "Ótimo": "#A3ED97",
                "Excelente": "#5ACF47"
            },
            hole=0.4
        )

        fig_pizza.update_traces(
            textinfo="label+value+percent",
            texttemplate="%{label}<br>%{value} aluno(s)<br>%{percent}",
            textfont=dict(size=14),
            pull=[0.04] * len(df_pizza)
        )

        fig_pizza.update_layout(
            showlegend=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(l=50, r=0, t=30, b=100)
        )

        st.plotly_chart(fig_pizza, width='stretch')

    # ---------------------------
    # Tabela por classificação
    # ---------------------------
    col3 = st.columns(1)[0]
    with col3:
        st.markdown(
            f"""
            <h3 style='color: #000000;'>
                📋 Relação de Alunos por Classificação na Turma: {turma_ano}: {turma_serie}ª série {turma_nome} ({turma_turno})
            </h3>
            <p style='font-size:16px; color:#666; margin-top:-10px;'>
                <em>Avaliação das Ilhas: Leitura, Escrita e Cálculo</em>
            </p>
            """,
            unsafe_allow_html=True
        )

        # ✅ Renomeando colunas para exibição mais amigável
        df_tabela = df_turma[[
            "classificacao",
            "soma_erros",
            "pts_ilha_leitura",
            "pts_ilha_escrita",
            "pts_ilha_calculo",
            "aluno_nome"
        ]].sort_values(by=["classificacao", "aluno_nome"]).reset_index(drop=True)

        df_tabela = df_tabela.rename(columns={
            "classificacao": "Classificação",
            "soma_erros": "Total de Erros",
            "pts_ilha_leitura": "Erros em Leitura",
            "pts_ilha_escrita": "Erros em Escrita",
            "pts_ilha_calculo": "Erros em Cálculo",
            "aluno_nome": "Nome do Aluno(a)"
        })

        def render_table_html(df):
            cores_classificacao = {
                "Grave": "#FF3A3A",
                "Crítico": "#FF7E7E",
                "Regular": "#FCA106",
                "Bom": "#FFCD32",
                "Ótimo": "#A3ED97",
                "Excelente": "#5ACF47"
            }

            html = "<table style='border-collapse: collapse; width: 100%; font-size: 16px;'>"
            html += "<tr>"
            for col in df.columns:
                html += f"<th style='border: 1px solid #ddd; padding: 8px; background-color:#f2f2f2'>{col}</th>"
            html += "</tr>"

            for _, row in df.iterrows():
                cor_fundo = cores_classificacao.get(row["Classificação"], "white")
                r, g, b = int(cor_fundo[1:3],16), int(cor_fundo[3:5],16), int(cor_fundo[5:7],16)
                luminancia = (0.299*r + 0.587*g + 0.114*b)
                texto = "black" if luminancia > 186 else "white"

                html += "<tr>"
                for col in df.columns:
                    html += f"<td style='border: 1px solid #ddd; padding: 8px; background-color:{cor_fundo}; color:{texto}; font-size:16px'>{row[col]}</td>"
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

        render_table_html(df_tabela)



