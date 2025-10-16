import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from config import engine
import logging
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

def escolasNoMapa():

    # -------------------------------------
    # ⚙️ Configurações da página
    # -------------------------------------
    st.markdown("""
    <style>
    [data-testid="stHeader"], div[role="banner"] { display: none !important; }
    body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBlock"], .main, .block-container {
        padding-top: 0 !important; margin-top: 0 !important;
    }

    /* Estiliza os contêineres dos selectbox */
    div[data-baseweb="select"] {
        border: 2px solid #4A90E2 !important;   /* Cor da borda */
        border-radius: 8px !important;          /* Bordas arredondadas */
        background-color: #ffffff !important;   /* Fundo branco */
        transition: all 0.3s ease;              /* Animação suave */
    }

    /* Efeito quando passa o mouse */
    div[data-baseweb="select"]:hover {
        border-color: #1A73E8 !important;       /* Azul mais escuro */
        box-shadow: 0 0 6px rgba(26, 115, 232, 0.4);
    }

    /* Efeito quando está em foco (clicado) */
    div[data-baseweb="select"]:focus-within {
        border-color: #1A73E8 !important;
        box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.3);
    }

    /* Ajuste do texto interno */
    div[data-baseweb="select"] > div {
        font-size: 14px !important;
        color: #333333 !important;
    }

    /* Ícone da setinha */
    div[data-baseweb="select"] svg {
        color: #4A90E2 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.set_page_config(page_title="Mapa de Escolas", page_icon="assets/favicon.ico", layout="wide")
    st.title("📊 Painel Estratégico - Mapa de Escolas")

    # -------------------------------------
    # 📦 Consulta ao banco de dados
    # -------------------------------------
    query = text("""
    SELECT 
        s.id AS school_id,
        s.name AS school_name,
        s.students_count,
        addr.state,
        addr.city,
        addr.zip_code,
        addr.latitude,
        addr.longitude,
        av.status AS avaliacao_status,
        COUNT(DISTINCT c.id) AS total_alunos_status
    FROM core.schools AS s
    JOIN auth.addresses AS addr 
        ON s.id = addr.school_id
    LEFT JOIN core.school_classes AS sc 
        ON s.id = sc.school_id
    LEFT JOIN core.children AS c 
        ON sc.id = c.class_id
    LEFT JOIN littera.children_avaliation AS av 
        ON c.id = av.child_id
    WHERE s.is_demo IS FALSE
    GROUP BY 
        s.id, s.name, s.students_count,
        addr.state, addr.city, addr.zip_code, addr.latitude, addr.longitude,
        av.status
    ORDER BY 
        s.name, av.status;
    """)

    try:
        df_original = pd.read_sql(query, engine)
    except OperationalError as e:
        logging.error(f"Erro ao conectar ao banco: {e}")
        st.error("Erro temporário ao conectar. Tente novamente mais tarde.")
        st.stop()
    except Exception as e:
        logging.error(f"Erro inesperado ao consultar dados: {e}")
        st.error("Erro inesperado. Tente novamente mais tarde.")
        st.stop()

    if df_original.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    # -------------------------------------
    # 🧹 Limpeza e preparação dos dados
    # -------------------------------------
    df_original['latitude'] = pd.to_numeric(df_original['latitude'], errors='coerce')
    df_original['longitude'] = pd.to_numeric(df_original['longitude'], errors='coerce')
    df_original = df_original.dropna(subset=['latitude', 'longitude'])

    # -------------------------------------
    # 🎛️ Filtros
    # -------------------------------------
    col1, col2, col3 = st.columns(3)

    # --- Estado ---
    estados = sorted(df_original['state'].unique())
    with col1:
        estado_sel = st.selectbox("Estado:", estados)

    # Filtra pelo estado
    df = df_original[df_original['state'] == estado_sel]

    # --- Cidade ---
    cidades = ["Todos"] + sorted(df['city'].unique())   # 👈 adiciona "Todos" no início da lista
    with col2:
        cidade_sel = st.selectbox("Cidade:", cidades)

    # Filtra pelo estado + cidade (se não for "Todos")
    if cidade_sel != "Todos":
        df = df[df['city'] == cidade_sel]

    # --- Métrica ---
    with col3:
        #st.metric('Total de Escolas', df.shape[0])
        st.metric('Total de Escolas', df['school_name'].nunique())

    # Caso não haja dados após os filtros
    if df.empty:
        st.warning("Nenhuma escola encontrada com os filtros selecionados.")
        st.stop()


    # -------------------------------------
    # 🧭 Função de deslocamento (jitter)
    # -------------------------------------
    def aplicar_deslocamento(dframe, offset=0.00090):
        coord_counts = {}
        latitudes, longitudes = [], []
        for _, row in dframe.iterrows():
            coord = (row['latitude'], row['longitude'])
            count = coord_counts.get(coord, 0)
            coord_counts[coord] = count + 1
            latitudes.append(row['latitude'] + count * offset)
            longitudes.append(row['longitude'] + count * offset)
        dframe = dframe.copy()
        dframe['lat_jitter'] = latitudes
        dframe['lon_jitter'] = longitudes
        return dframe

    df = aplicar_deslocamento(df)

    # -------------------------------------
    # 🧹 Agrupamento por escola para o mapa
    # -------------------------------------
    # Agrupa os status por escola em um dicionário {status: total}
    status_por_escola = (
        df.groupby(['school_id', 'school_name', 'state', 'city', 'zip_code', 'latitude', 'longitude', 'students_count'])
        .apply(lambda g: {row['avaliacao_status']: row['total_alunos_status'] for _, row in g.iterrows()})
        .reset_index(name='status_dict')
    )

    # Dicionário de mapeamento
    status_labels = {
        "NaoIniciado": "Não Iniciado",
        "EmAndamento": "Em Andamento",
        "Concluido": "Concluído"
    }

    # Função para formatar o tooltip com labels amigáveis
    def formatar_status(status_dict):
        if not status_dict:
            return "Nenhum status disponível"
        linhas = [f"{status_labels.get(status, status)}: {qtd}" for status, qtd in status_dict.items()]
        return "<br>".join(linhas)

    # Aplica no dataframe
    status_por_escola['tooltip_text'] = status_por_escola['status_dict'].apply(formatar_status)

    # Aplica deslocamento para evitar sobreposição de marcadores
    status_por_escola = aplicar_deslocamento(status_por_escola)

    # -------------------------------------
    # 🗺️ Mapa Folium (ajustado)
    # -------------------------------------
    lat_inicial = status_por_escola.iloc[0]['lat_jitter']
    lon_inicial = status_por_escola.iloc[0]['lon_jitter']
    m = folium.Map(location=[lat_inicial, lon_inicial], zoom_start=10, tiles='OpenStreetMap')

    if status_por_escola.shape[0] > 500:
        marker_container = MarkerCluster().add_to(m)
    else:
        marker_container = m

    for _, row in status_por_escola.iterrows():
        popup = f"""
        <b>{row['school_name']}</b><br>
        {row['city']} - {row['state']}<br>
        Total de Alunos Cadastrados: {row['students_count']}<br>
        <br>
        <b>Status de Avaliação</b><br>
        {row['tooltip_text']}
        """
        folium.Marker(
            location=[row['lat_jitter'], row['lon_jitter']],
            tooltip=popup,
            icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
        ).add_to(marker_container)


    # -------------------------------------
    # 📊 Layout final
    # -------------------------------------
    st_folium(m, use_container_width=True, returned_objects=[])

    #st.dataframe(df.reset_index(drop=True))

