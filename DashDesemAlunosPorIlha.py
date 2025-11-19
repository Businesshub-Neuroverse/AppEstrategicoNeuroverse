import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import executar_query
from sqlalchemy.exc import OperationalError
import logging

# ================================
# DASHBOARD PRINCIPAL
# ================================
def dashboardDesAlunoIlha(email_hash=None):

    # ----------------------------------------------------------
    # QUERY
    # ----------------------------------------------------------
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
        av.lectio_score AS pts_ilha_letras_palavras,
        av.visualis_score AS pts_ilha_atencao_visual,
        av.grafomo_score AS pts_ilha_habilidades_motoras,
        av.meta_score AS pts_ilha_rima,
        av.opus_score AS pts_ilha_memoria,
        av.calculum_score AS pts_ilha_calculo
    FROM auth.users u
    JOIN auth.school_users su ON u.id = su.user_id
    JOIN core.schools s ON su.school_id = s.id
    JOIN core.school_classes t ON s.id = t.school_id
    JOIN core.children a ON t.id = a.class_id
    JOIN littera.children_avaliation av ON a.id = av.child_id
    WHERE av.status = 'Concluido'
    AND u.email_hash = :email_hash
    ORDER BY t.grade;
    """

    # ----------------------------------------------------------
    # EXECUTAR QUERY
    # ----------------------------------------------------------
    try:
        df = executar_query(query, params={"email_hash": email_hash})
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

    # ----------------------------------------------------------
    # IDENTIFICADOR COMPLETO DA TURMA
    # ----------------------------------------------------------
    df["turma_id"] = (
        df["turma_ano"].astype(str) + ": " +
        df["turma_serie"].astype(str) + "ª série " +
        df["turma_nome"].astype(str) + " " +
        df["turma_turno"].astype(str)
    )

    # ----------------------------------------------------------
    # CONFIG STREAMLIT
    # ----------------------------------------------------------
    st.set_page_config(
        page_title="Alunos x Ilhas",
        page_icon="📊",
        layout="wide"
    )

    st.markdown(
        "<h2 style='color: #5A6ACF;'>📊 Desempenho dos Alunos e Turmas nas Ilhas do Conhecimento e Habilidades</h2>",
        unsafe_allow_html=True
    )

    # ----------------------------------------------------------
    # CSS — CARDS MODERNOS
    # ----------------------------------------------------------
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
        CARDS MODERNOS
        ----------------------------- */
        .card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            text-align: center;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        .card-title {
            font-size: 16px;
            color: #444;
            font-weight: 600;
        }
        .card-value {
            font-size: 28px;
            font-weight: 800;
            color: #5A6ACF;
        }
        .card-sub {
            font-size: 14px;
            color: #666;
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

    # ----------------------------------------------------------
    # LISTA DE ILHAS
    # ----------------------------------------------------------
    ILHAS = [
        "pts_ilha_leitura",
        "pts_ilha_escrita",
        "pts_ilha_letras_palavras",
        "pts_ilha_atencao_visual",
        "pts_ilha_habilidades_motoras",
        "pts_ilha_rima",
        "pts_ilha_memoria",
        "pts_ilha_calculo"
    ]

    ILHAS_LABELS = {
        "pts_ilha_leitura": "Leitura",
        "pts_ilha_escrita": "Escrita",
        "pts_ilha_letras_palavras": "Letras e Palavras",
        "pts_ilha_atencao_visual": "Atenção Visual",
        "pts_ilha_habilidades_motoras": "Habilidades Motoras",
        "pts_ilha_rima": "Rima",
        "pts_ilha_memoria": "Memória",
        "pts_ilha_calculo": "Cálculo"
    }

    # ----------------------------------------------------------
    # MULTISELECT COM TRATAMENTO "TODOS"
    # ----------------------------------------------------------
    turmas = sorted(df["turma_id"].unique())
    opcoes_turmas = ["Todos"] + turmas

    turma_select = st.multiselect(
        "Selecione uma ou mais turmas:",
        opcoes_turmas,
        default=["Todos"]
    )

    # Se apagar tudo → volta para "Todos"
    if not turma_select:
        turma_select = ["Todos"]
    

    # Se selecionar "Todos" + outras → mantém só "Todos"
    if "Todos" in turma_select and len(turma_select) > 1:
        turma_select = ["Todos"]

    # Filtrar DF
    if "Todos" in turma_select:
        df = df.copy()
    else:
        df = df[df["turma_id"].isin(turma_select)]

    # ----------------------------------------------------------
    # CARDS DE MÉTRICAS
    # ----------------------------------------------------------
    total_alunos = df["aluno_nome"].nunique()
    total_turmas = df["turma_id"].nunique()

    media_geral_erros = df[ILHAS].mean().mean().round(2)

    df_mean_global = df[ILHAS].mean()
    pior_ilha = ILHAS_LABELS[df_mean_global.idxmax()]
    pior_valor = df_mean_global.max().round(2)

    colA, colB, colC, colD = st.columns(4)

    with colA:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Total de Alunos</div>
            <div class="card-value">{total_alunos}</div>
            <div class="card-sub">Alunos avaliados</div>
        </div>
        """, unsafe_allow_html=True)

    with colB:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Total de Turmas</div>
            <div class="card-value">{total_turmas}</div>
            <div class="card-sub">Turmas analisadas</div>
        </div>
        """, unsafe_allow_html=True)

    with colC:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Média Geral de Erros</div>
            <div class="card-value">{media_geral_erros}</div>
            <div class="card-sub">Entre todas as ilhas</div>
        </div>
        """, unsafe_allow_html=True)

    with colD:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Pior Ilha</div>
            <div class="card-value">{pior_ilha}</div>
            <div class="card-sub">{pior_valor} erros (média)</div>
        </div>
        """, unsafe_allow_html=True)

    #st.markdown("---")

    # ----------------------------------------------------------
    # ABAS
    # ----------------------------------------------------------
    aba1, aba2, aba3 = st.tabs([
        "📌 Radar por Aluno",
        "🔥 Heatmap por Turma",
        "📈 Barras por Ilha"
    ])

    # ----------------------------------------------------------
    # ABA 1 – RADAR + PIZZA
    # ----------------------------------------------------------
    with aba1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📌 Radar de Desempenho por Ilha")

            aluno = st.selectbox("Selecione o aluno:", df["aluno_nome"].unique())

            st.caption("🔹 No gráfico de pizza, cada fatia refere-se a ilha com pelo menos 'Um Erro' cometido pelo aluno acima selecionado.")

            df_aluno = df[df["aluno_nome"] == aluno].iloc[0]
            valores = [df_aluno[i] for i in ILHAS]
            labels = list(ILHAS_LABELS.values())

            # -----------------------------
            # TABELA VERTICAL AJUSTADA
            # -----------------------------
            #df_vertical = (
             #   pd.DataFrame({
              #      "Ilha": [ILHAS_LABELS[i] for i in ILHAS],
               #     "Erros": [df_aluno[i] for i in ILHAS]
                #})
            #)

            st.markdown(f"""
            <div style="
                padding: 15px;
                border-radius: 12px;
                background-color: #ffffff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            ">
                <strong>Aluno:</strong> {df_aluno["aluno_nome"]}
                <strong>Turma:</strong> {df_aluno["turma_id"]}
            </div>
            """, unsafe_allow_html=True)


            #st.write("### 📊 Erros por Ilha")
            #st.write(df_vertical)


        with col2:
            st.subheader("📊 Distribuição de Erros por Ilha")

            df_pizza = pd.DataFrame({
                "Ilha": labels,
                "Erros": valores
            })

            fig_pizza = px.pie(
                df_pizza,
                names="Ilha",
                values="Erros",
                hole=0.1
            )

            fig_pizza.update_layout(
                height=500,
                margin=dict(l=50, r=50, t=0, b=20)
            )

            fig_pizza.update_traces(
                textinfo="label+value+percent",
                textposition="inside",
                textfont=dict(size=14),
                pull=[0.02] * len(df_pizza)
            )

            st.plotly_chart(fig_pizza, width='stretch')

    # ----------------------------------------------------------
    # ABA 2 – HEATMAP
    # ----------------------------------------------------------
    with aba2:
        st.subheader("🔥 Heatmap das Turmas (Médias de Erros por Ilha)")

        df_mean = df.groupby("turma_id")[ILHAS].mean().round(2).reset_index()

        fig_heat = px.imshow(
            df_mean.set_index("turma_id").rename(columns=ILHAS_LABELS),
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Reds"
        )

        fig_heat.update_layout(
            height=500,
            yaxis_title="Turmas",   # ← novo label do eixo Y
            margin=dict(l=50, r=50, t=10, b=20)
        )

        st.plotly_chart(fig_heat, width='stretch')

    # ----------------------------------------------------------
    # ABA 3 – BARRAS
    # ----------------------------------------------------------
    with aba3:
        st.subheader("📈 Comparativo de Média de Erros das Turmas por Ilha")

        df_melt = df_mean.melt(
            id_vars="turma_id",
            var_name="Ilha",
            value_name="Erros"
        )

        df_melt["Ilha"] = df_melt["Ilha"].map(ILHAS_LABELS)

        fig_bar = px.bar(
            df_melt,
            x="Ilha",
            y="Erros",
            text="Erros",
            color="turma_id",
            labels={"turma_id":"Turmas", "Erros" : "Média de Erros"},
            barmode="group"
        )

        #fig_bar.update_layout(height=500)

        fig_bar.update_layout(
            height=500,
            margin=dict(l=50, r=50, t=10, b=20)
        )

        st.plotly_chart(fig_bar, width='stretch')