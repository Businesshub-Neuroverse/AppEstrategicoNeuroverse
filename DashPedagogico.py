# Biblioteca para análise e manipulação de dados
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import streamlit as st
import numpy as np
from sqlalchemy import text
from config import executar_query
from sqlalchemy.exc import OperationalError
import logging

def dashboardPedagogico(email_hash=None):
    
    # ---------------------------
    # Estilo da página
    # ---------------------------
    st.markdown("""
    <style>
        /* -----------------------------
        REMOVER HEADER E AJUSTAR LAYOUT
        ----------------------------- */
        [data-testid="stHeader"], 
        div[role="banner"] { 
            display: none !important; 
        }

        body, .stApp, [data-testid="stAppViewContainer"], 
        [data-testid="stBlock"], .main, .block-container {
            padding-top: 0 !important; 
            margin-top: 0 !important;
        }
        
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

    st.set_page_config(page_title="Dash Pedagógico", page_icon="assets/favicon.ico", layout="wide")
    st.markdown("<h2 style='color: #5A6ACF;'>📊 Desempenho Geral Pedagógico das Escolas</h2>", unsafe_allow_html=True)

    # ---------------------------
    # Consulta SQL
    # ---------------------------
    query = """
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
        av.interpretation_score AS pts_ilha_interpretacao,
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
    # Layout de seleção
    # ---------------------------
    todas_escolas = sorted(df["escola_nome"].unique())
    escola_select = st.multiselect("Selecione uma ou mais turmas:",  todas_escolas, default=[todas_escolas[0]])

    if not escola_select:
        escola_select = [todas_escolas[0]]
        df_filtrado = df[df["escola_nome"].isin(escola_select)]
    else:
        df_filtrado = df[df["escola_nome"].isin(escola_select)]
    

    # ---------------------------
    # Cores e função de pontuação
    # ---------------------------
    classes = {
        "Muito Acima do Esperado": "#4AA63B",
        "Acima do Esperado": "#5ACF47",
        "Dentro do Esperado": "#A3ED97",
        "Abaixo do esperado": "#FFCD32",
        "Alerta leve": "#FCA106",
        "Alerta moderado": "#FF7E7E",
        "Alerta grave": "#FF3A3A",
    }

    def cor_por_pontuacao(p):
        if p <= 5: return "#4AA63B"
        elif p <= 8: return "#5ACF47"
        elif p <= 14: return "#A3ED97"
        elif p <= 18: return "#FFCD32"
        elif p <= 31: return "#FCA106"
        elif p <= 44: return "#FF7E7E"
        else: return "#FF3A3A"

    # ---------------------------
    # Gráfico empilhado
    # ---------------------------
    df_stack = df_filtrado.groupby(["classificacao_aluno","escola_nome"], as_index=False).agg(qtd_alunosAvaliados=("aluno_nome","count"))

    df_media = df_filtrado.groupby("escola_nome")["avaliacao_erros"].mean().reset_index()
    df_media["cor_media"] = df_media["avaliacao_erros"].apply(cor_por_pontuacao)
    df_media["escola_label"] = df_media["escola_nome"] + " (" + df_media["avaliacao_erros"].round(1).astype(str) + " Me Erros)"
    df_stack = df_stack.merge(df_media[["escola_nome","escola_label","cor_media"]], on="escola_nome", how="left")

    df_stack["texto_barra"] = df_stack["qtd_alunosAvaliados"].astype(str)
    df_stack["eixo_XQtd_Alunos"] = df_stack["qtd_alunosAvaliados"].astype(str)

    if df_stack.empty:
        st.warning("Sem dados para montar gráfico.")
        return

    fig_stack = px.bar(
        df_stack,
        x="eixo_XQtd_Alunos",
        y="escola_label",
        color="classificacao_aluno",
        color_discrete_map=classes,
        text="texto_barra",
        orientation="h",
        title="Desempenho Classificatório por Escola e Alunos",
        labels={"eixo_XQtd_Alunos":"Quantidade de Alunos Avaliados", "escola_label":"","texto_barra":"Resumo"}
    )

    fig_stack.update_layout(
        title=dict(text="Classificatório por Escola e Alunos", font=dict(size=20), x=0.5, xanchor='center'),
        hovermode="closest",
        showlegend=True,
        paper_bgcolor='white',
        plot_bgcolor="white",
        autosize=True,
        margin=dict(l=10,r=0,t=80,b=80),
        xaxis=dict(title=dict(text="Quantidade de Alunos Avaliados", font=dict(size=16)), tickfont=dict(size=14), automargin=True),
        yaxis=dict(title=dict(text=""), tickfont=dict(size=14), automargin=True)
    )

    fig_stack.update_traces(textfont=dict(size=14, color="black"), insidetextanchor="middle")

    # ---------------------------
    # Captura clique
    # ---------------------------
    selected_points = plotly_events(fig_stack, select_event=True, key="stack_click", override_height=None, override_width=None)
    
    escola_clicked = df_stack["escola_label"].iloc[0]
    classif_clicked = df_stack["classificacao_aluno"].iloc[0]
    if selected_points:
        ponto = selected_points[0]
        escola_clicked = ponto.get("y") or escola_clicked
        curva_idx = int(ponto.get("curveNumber",0))
        try:
            classif_clicked = fig_stack.data[curva_idx].name
        except Exception:
            classif_clicked = df_stack["classificacao_aluno"].unique()[0]

    # ---------------------------
    # Tabela final por escola e classificação
    # ---------------------------
    escola_nome_real = escola_clicked.split(" (")[0]
    df_ilhas = df_filtrado[(df_filtrado["escola_nome"]==escola_nome_real) & (df_filtrado["classificacao_aluno"]==classif_clicked)]
    if df_ilhas.empty:
        df_ilhas = df_filtrado[df_filtrado["escola_nome"]==escola_nome_real]

    colunas_ilhas = [
        "pts_ilha_leitura","pts_ilha_escrita","pts_ilha_visual",
        "pts_ilha_calculo","pts_ilha_motora","pts_ilha_rima",
        "pts_ilha_interpretacao","pts_ilha_memoria"
    ]

    labels_ilhas = {
        "pts_ilha_leitura":"Leitura","pts_ilha_escrita":"Escrita","pts_ilha_visual":"Visual",
        "pts_ilha_calculo":"Cálculo","pts_ilha_motora":"Motora","pts_ilha_rima":"Rima",
        "pts_ilha_interpretacao":"Interpretação","pts_ilha_memoria":"Memória","avaliacao_erros":"Erros Totais"
    }

    df_tabela = df_ilhas.groupby(["aluno_nome","classificacao_aluno"], as_index=False).mean(numeric_only=True)
    df_tabela[colunas_ilhas] = df_tabela[colunas_ilhas].round(1)

    colunas_final = ["aluno_nome","avaliacao_erros"] + colunas_ilhas
    df_tabela = df_tabela[colunas_final].rename(columns={"aluno_nome":"Aluno", **labels_ilhas})

    def colorir_linha_por_pg(row):
        cor = cor_por_pontuacao(row["Erros Totais"])
        return [f'background-color: {cor}; color: black'] * len(row)

    df_styled = df_tabela.style.apply(colorir_linha_por_pg, axis=1).format(precision=1).hide(axis="index")

    # ---------------------------
    # Exibe gráfico e tabela
    # ---------------------------
    st.markdown(f"### 🔎 **{escola_clicked}** - Alunos: **<span style='color:#5A6ACF; font-size:30px;'>{classif_clicked}</span>**", unsafe_allow_html=True)

    st.dataframe(df_styled)










