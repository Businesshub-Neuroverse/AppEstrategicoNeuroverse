
# Biblioteca para análise e manipulação de dados
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import streamlit as st
import numpy as np
from sqlalchemy import text
from config import engine  # importa a engine pronta
from sqlalchemy.exc import OperationalError
import logging

# -----------------------
# Forçar tema claro (branco) com CSS customizado
# -----------------------
st.markdown(
    """
    <style>
        /* 🌟 Fundo geral da aplicação */
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }

        /* 🌟 Barra lateral */
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            color: #000000;
        }

        /* 🌟 Títulos e textos */
        h1, h2, h3, h4, h5, h6, p, span, label, div {
            color: #000000 !important;
        }

        /* 🌟 Botões */
        .stButton > button {
            background-color: #E9ECEF;
            color: #000000;
            border: 1px solid #CED4DA;
            border-radius: 5px;
        }
        .stButton > button:hover {
            background-color: #DEE2E6;
            color: #000000;
        }

        /* 🌟 Inputs de texto, números, etc */
        .stTextInput > div > div > input,
        .stNumberInput input,
        .stTextArea textarea {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CED4DA;
            border-radius: 5px;
        }

        /* 🌟 Selectbox e multiselect */
        /* Caixa de seleção do multiselect e selectbox */
        .stSelectbox div[data-baseweb="select"],
        .stMultiSelect div[data-baseweb="select"] {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CED4DA;
            border-radius: 5px;
        }

        /* Itens da lista dropdown (as opções) */
        .stSelectbox div[data-baseweb="popover"] div[role="listbox"] div[role="option"],
        .stMultiSelect div[data-baseweb="popover"] div[role="listbox"] div[role="option"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        /* Item da lista quando passa o mouse por cima (hover) */
        .stSelectbox div[data-baseweb="popover"] div[role="listbox"] div[role="option"]:hover,
        .stMultiSelect div[data-baseweb="popover"] div[role="listbox"] div[role="option"]:hover {
            background-color: #E9ECEF !important;
            color: #000000 !important;
        }

        /* Tags de itens já selecionados no multiselect */
        .stMultiSelect div[data-baseweb="tag"] {
            background-color: #F8F9FA !important;
            color: #000000 !important;
            border: 1px solid #CED4DA !important;
        }

        /* 🌟 Tabelas */
        .stDataFrame,
        .stTable {
            background-color: #FFFFFF;
            color: #000000;
        }

        /* 🌟 Caixas de métricas e cards */
        [data-testid="stMetricValue"] {
            color: #000000;
        }
        [data-testid="stMetricLabel"] {
            color: #000000;
        }
    </style>
    """,
    unsafe_allow_html=True
)

def dashboardPedegogico(email_hash=None):

    # -------------------------
    # Layout da Página
    # -------------------------
    st.set_page_config(page_title="Dash Pedagógico", page_icon="assets/favicon.ico", layout="wide")
    st.title("📊 Desempenho Geral Pedagógico")

    query = text("""
    SELECT 
        u.email_hash AS hash_email,
        s.name AS escola_nome,
        s.students_count AS escola_qtdAlunos,
        t.education_level AS turma_nivel,
        t.shift AS turma_turno,
        t.grade AS turma_serie,
        t.name AS turma_nome,
        t.year AS turma_ano,
        a.name AS aluno_nome,
        av.status AS avaliacao_status,
        av.classification_score AS avaliacao_classif,
        av.error_score AS avaliacao_erros,
        av.lectio_score AS pts_ilha_leitura,
        av.scriptura_score AS pts_ilha_escrita,
        av.visualis_score AS pts_ilha_visual,
        av.calculum_score AS pts_ilha_calculo,
        av.grafomo_score AS pts_ilha_motora,
        av.meta_score AS pts_ilha_rima,
        av.nominare_score AS pts_ilha_fala,
        av.opus_score AS pts_ilha_memoria,
        cl.label AS classificacao_aluno,
        cl.description AS classif_aluno_desc
    FROM auth.users u
    JOIN auth.school_users su ON u.id = su.user_id
    JOIN core.schools s ON su.school_id = s.id
    JOIN core.school_classes t ON s.id = t.school_id
    JOIN core.children a ON t.id = a.class_id
    JOIN littera.children_avaliation av ON a.id = av.child_id
    JOIN littera.children_classification cl ON av.classification_id = cl.id
    WHERE av.status = 'Concluido'
    AND u.email_hash = :email_hash
    ORDER BY av.classification_score
    """)

    # -----------------------------
    # Ler dados
    # -----------------------------
    try:
        df = pd.read_sql(query, engine, params={"email_hash": email_hash})
    except OperationalError as e:
        logging.error(f"Falha operacional ao conectar banco no consultar escolas/alunos: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        df = pd.DataFrame()
    except Exception as e:
        logging.error(f"Erro inesperado ao consultar dados escolas/alunos: {e}")
        st.error("Ocorreu um erro inesperado. Tente novamente mais tarde.")
        df = pd.DataFrame()


    if df.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    # ---------------------------
    # 🔹 Filtros na barra lateral
    # ---------------------------
    st.sidebar.header("Filtros")

    filtro_classificacao = st.sidebar.multiselect(
        "Pesquisar por Classificação",
        options=df["classificacao_aluno"].unique(),
        placeholder="Selecione uma ou mais"
    )

    filtro_escola = st.sidebar.multiselect(
        "Pesquisar por Escola",
        options=df["escola_nome"].unique(),
        placeholder="Selecione uma ou mais"
    )

    # Cards coloridos de referência
    st.sidebar.subheader("Referência - Classificação")
    classes = {
        "Muito Acima do Esperado": "#4AA63B",
        "Acima do Esperado": "#5ACF47",
        "Dentro do Esperado": "#A3ED97",
        "Alerta para Déficit": "#FFCD32",
        "Déficit leve": "#FCA106",
        "Déficit moderado": "#FF7E7E",
        "Déficit grave": "#FF3A3A",
    }

    faixas_classificacao = {
        "Muito Acima do Esperado": "<=5",
        "Acima do Esperado": ">5 e <=8",
        "Dentro do Esperado": ">8 e <=14",
        "Alerta para Déficit": ">14 e <=18",
        "Déficit leve": ">18 e <=31",
        "Déficit moderado": ">31 e <=44",
        "Déficit grave": ">45 e <=100",
    }

    for nome, cor in classes.items():
        faixa = faixas_classificacao[nome]
        st.sidebar.markdown(
            f"""
            <div style='background-color:{cor}; 
                        padding:3px; 
                        border-radius:8px; 
                        margin-bottom:6px; 
                        font-size:12px; 
                        color:black; 
                        font-weight:bold;
                        text-align:center;'>{nome} <span style='font-weight:normal;'>{faixa} Pts</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------------------------
    # Filtrar DataFrame
    # ---------------------------
    df_filtrado = df.copy()
    if filtro_classificacao:
        df_filtrado = df_filtrado[df_filtrado["classificacao_aluno"].isin(filtro_classificacao)]
    if filtro_escola:
        df_filtrado = df_filtrado[df_filtrado["escola_nome"].isin(filtro_escola)]

    if df_filtrado.empty:
        st.info("Sem dados para os filtros selecionados.")
        st.stop()

    # -----------------------------
    # Layout principal
    # -----------------------------
    col1 = st.columns(1)[0]
    col2 = st.columns(1)[0]

    # ---------------------------
    # Função para cor pela pontuação
    # ---------------------------
    def cor_por_pontuacao(p):
        if p <= 5:
            return "#4AA63B"
        elif p <= 8:
            return "#5ACF47"
        elif p <= 14:
            return "#A3ED97"
        elif p <= 18:
            return "#FFCD32"
        elif p <= 31:
            return "#FCA106"
        elif p <= 44:
            return "#FF7E7E"
        else:
            return "#FF3A3A"

    # ---------------------------
    # 1. Gráfico de Barras empilhadas (clicável)
    # ---------------------------
    df_stack = df_filtrado.groupby(
    ["classificacao_aluno", "escola_nome"], as_index=False
    ).agg(qtd_alunosAvaliados=("aluno_nome", "count"))

    df_media = df_filtrado.groupby("escola_nome")["avaliacao_classif"].mean().reset_index()
    df_media["cor_media"] = df_media["avaliacao_classif"].apply(cor_por_pontuacao)
    df_media["escola_label"] = df_media["escola_nome"] + " (" + df_media["avaliacao_classif"].round(1).astype(str) + " pts)"

    df_stack = df_stack.merge(df_media[["escola_nome", "escola_label", "cor_media"]], on="escola_nome", how="left")
    df_stack["texto_barra"] = df_stack["qtd_alunosAvaliados"].astype(str)

    df_stack["eixo_XQtd_Alunos"] = df_stack["qtd_alunosAvaliados"].astype(str)

    fig_stack = px.bar(
        df_stack,
        x="eixo_XQtd_Alunos",
        y="escola_label",
        color="classificacao_aluno",
        color_discrete_map=classes,
        text="texto_barra",
        orientation="h",
        title="Desempenho Classificatório por Escola e Alunos - Clique na Barra para Detalhar",
        labels={"eixo_XQtd_Alunos": "Quantidade de Alunos Avaliados", "escola_label": "", "texto_barra" : "Resumo"}
    )

    fig_stack.update_layout(
        yaxis=dict(title="", automargin=True),
        xaxis=dict(title="Quantidade de Alunos Avaliados", automargin=True),
        hovermode="closest",
        showlegend=False
    )

    with col1:
        selected_points = plotly_events(fig_stack, select_event=True, key="stack_click")

    # ---------------------------
    # 2. Tabela Interativa
    # ---------------------------
    colunas_ilhas = [
        "pts_ilha_leitura", "pts_ilha_escrita", "pts_ilha_visual",
        "pts_ilha_calculo", "pts_ilha_motora", "pts_ilha_rima",
        "pts_ilha_fala", "pts_ilha_memoria"
    ]

    labels_ilhas = {
        "pts_ilha_leitura": "Leitura",
        "pts_ilha_escrita": "Escrita",
        "pts_ilha_visual": "Visual",
        "pts_ilha_calculo": "Cálculo",
        "pts_ilha_motora": "Motora",
        "pts_ilha_rima": "Rima",
        "pts_ilha_fala": "Fala",
        "pts_ilha_memoria": "Memória",
        "avaliacao_erros": "Erros Totais"
    }

    df_ilhas = df_filtrado[["aluno_nome", "escola_nome", "classificacao_aluno", "avaliacao_classif", "avaliacao_erros"] + colunas_ilhas]

    # 🔹 Se não houver clique, simula seleção do primeiro ponto da barra
    if selected_points:
        ponto = selected_points[0]
    else:
        # Pega o primeiro trace (primeira classificação) e o primeiro ponto
        ponto = {"y": df_stack["escola_label"].iloc[0], "curveNumber": 0}

    escola_clicked = ponto["y"]                   # Nome da escola (vem do eixo Y)
    curva_idx = ponto["curveNumber"]              # Índice do trace (classificação clicada)
    classif_clicked = fig_stack.data[curva_idx].name  # Nome do trace = classificação

    df_ilhas = df_ilhas[
        (df_ilhas["escola_nome"] == escola_clicked.split(" (")[0]) &
        (df_ilhas["classificacao_aluno"] == classif_clicked)
    ]

    df_tabela = df_ilhas.groupby(["aluno_nome", "classificacao_aluno"], as_index=False).mean(numeric_only=True)
    df_tabela[colunas_ilhas] = df_tabela[colunas_ilhas].round(1)
    df_tabela["avaliacao_classif"] = df_tabela["avaliacao_classif"].round(1)
    df_tabela = df_tabela.rename(columns={"avaliacao_classif": "Pontuação Geral"})

    colunas_final = ["aluno_nome", "Pontuação Geral", "avaliacao_erros"] + colunas_ilhas
    df_tabela = df_tabela[colunas_final]
    df_tabela = df_tabela.rename(columns={"aluno_nome": "Aluno", **labels_ilhas})

    def colorir_linha_por_pg(row):
        cor = cor_por_pontuacao(row["Pontuação Geral"])
        return [f'background-color: {cor}; color: black'] * len(row)

    df_styled = df_tabela.style.apply(colorir_linha_por_pg, axis=1).format(precision=1).hide(axis="index")

    with col2:
            st.markdown(f"### 🔎 **{escola_clicked}** - Alunos: **{classif_clicked}**")
            st.dataframe(df_styled, use_container_width=True)






