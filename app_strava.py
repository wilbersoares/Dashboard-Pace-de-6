import pandas as pd
import plotly.express as px
import polyline
import requests
import streamlit as st
from datetime import datetime, timedelta
from urllib.parse import quote

from correlacao import exibir_correlacao
from desempenho_corridas import exibir_desempenho_corridas
from evolucao_provas import exibir_evolucao_provas
from evolucao_tempo import exibir_evolucao_tempo

# -------------------------------------------------------------------
# 1. CONFIG & ESTILO
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Dashboard Strava | Pace de 6",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORWAY = ["#FF4B4B", "#0ea5e9", "#22c55e", "#f59e0b", "#a855f7", "#10b981"]
PRIMARY_COLOR = COLORWAY[0]


def _theme_tokens():
    base = (st.get_option("theme.base") or "light").lower()
    is_dark = base == "dark"
    background = "#0b1221" if is_dark else "#f8fafc"
    font = "#e2e8f0" if is_dark else "#0f172a"
    kpi_surface = "#111827" if is_dark else background
    template = "plotly_dark" if is_dark else "plotly_white"
    return {"background": background, "font": font, "kpi": kpi_surface, "template": template}


def estilizar_plot(fig):
    tokens = _theme_tokens()
    fig.update_layout(
        template=tokens["template"],
        colorway=COLORWAY,
        plot_bgcolor=tokens["background"],
        paper_bgcolor=tokens["background"],
        font=dict(color=tokens["font"], size=13),
        margin=dict(l=0, r=0, t=50, b=30),
    )
    return fig


# -------------------------------------------------------------------
# 2. CAMADA DE API (STRAVA + CLIMA)
# -------------------------------------------------------------------

@st.cache_data(ttl=86400)  # 1 dia
def carregar_dados_atleta(url: str, headers: dict):
    """Busca os dados do perfil do atleta (GET /athlete)."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as e:
        return None, f"Erro ao buscar dados do atleta: {e}"


@st.cache_data(ttl=900)  # 15 min
def carregar_clima(cidade: str | None) -> str:
    """Busca o clima atual da cidade usando a API gratuita wttr.in."""
    if not cidade:
        return "Clima (cidade não informada)"
    try:
        cidade_url = quote(cidade)
        url_clima = f"https://wttr.in/{cidade_url}?format=j1"
        response = requests.get(url_clima, timeout=10)
        response.raise_for_status()

        dados = response.json()
        condition = dados.get("current_condition", [{}])[0]
        temp_c = condition.get("temp_C")
        lang_pt = condition.get("lang_pt", [{}])[0]
        desc = lang_pt.get("value")

        if temp_c and desc:
            return f"{temp_c}°C, {desc}"
        if temp_c:
            return f"{temp_c}°C"
        return "Dados de clima incompletos"
    except requests.RequestException as e:
        print(f"ERRO AO BUSCAR CLIMA: {e}")
        return "Clima indisponível"


@st.cache_data(ttl=3600)  # 1 hora
def carregar_todas_atividades(url: str, headers: dict):
    """
    Busca TODAS as atividades do atleta, página por página.
    Retorna (DataFrame, ErrorMessage)
    """
    todas_atividades: list[dict] = []
    pagina = 1
    per_page = 100

    while True:
        try:
            params = {"page": pagina, "per_page": per_page}
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            dados_pagina = response.json()
            if not dados_pagina:
                break
            todas_atividades.extend(dados_pagina)
            pagina += 1
        except requests.RequestException as e:
            return None, f"Erro ao buscar atividades (página {pagina}): {e}"

    if not todas_atividades:
        return None, "Nenhuma atividade encontrada."

    df = pd.DataFrame(todas_atividades)
    return df, None


@st.cache_data(ttl=3600)
def carregar_detalhes_atividade(activity_id: int, headers: dict, url_base: str):
    """Busca os detalhes completos de UMA atividade (splits, segmentos, mapa)."""
    url = f"{url_base}/activities/{activity_id}"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as e:
        return None, f"Erro ao buscar /activities/{activity_id}: {e}"


# -------------------------------------------------------------------
# 3. REGRAS DE NEGÓCIO
# -------------------------------------------------------------------

TRADUCOES_TIPO = {
    "Run": "Corrida",
    "Ride": "Ciclismo",
    "Swim": "Natação",
    "Walk": "Caminhada",
    "Hike": "Trilha",
    "TrailRun": "Corrida em Trilha",
    "WeightTraining": "Musculação",
    "Yoga": "Yoga",
    "Workout": "Treino Geral",
}


def obter_saudacao() -> str:
    """Verifica a hora local do servidor e retorna a saudação correta."""
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia"
    if 12 <= hora < 18:
        return "Boa tarde"
    return "Boa noite"


@st.cache_data
def tratar_dados(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """Aplica transformações e campos derivados nas atividades."""
    df = df_bruto.copy()
    for col, default in [
        ("distance", 0),
        ("moving_time", 0),
        ("average_speed", 0),
        ("total_elevation_gain", 0),
        ("kudos_count", 0),
        ("average_heartrate", 0),
        ("max_speed", 0),
        ("average_watts", 0),
        ("workout_type", 0),
    ]:
        if col not in df.columns:
            df[col] = default

    df["distancia_km"] = (df["distance"] / 1000).round(2)
    df["tempo_horas"] = (df["moving_time"] / 3600).round(2)
    df["tempo_total_segundos"] = df["moving_time"]
    df["vel_media_kmh"] = (df["average_speed"] * 3.6).round(2)
    df["pace_min_km"] = 0.0
    mask_vel = df["vel_media_kmh"] > 0
    df.loc[mask_vel, "pace_min_km"] = 60 / df.loc[mask_vel, "vel_media_kmh"]

    def formatar_pace(pace_decimal: float) -> str:
        if pace_decimal <= 0:
            return "N/A"
        minutos = int(pace_decimal)
        segundos = int((pace_decimal * 60) % 60)
        return f"{minutos:02}:{segundos:02} min/km"

    df["pace_formatado"] = df["pace_min_km"].apply(formatar_pace)
    df["data_inicio"] = pd.to_datetime(df["start_date_local"])
    df["ano"] = df["data_inicio"].dt.year
    df["display_name"] = df["data_inicio"].dt.strftime("%Y-%m-%d") + " | " + df["name"]
    df["tipo_traduzido"] = df["type"].map(TRADUCOES_TIPO).fillna(df["type"])

    # Classificação de Corridas (Prova)
    def classificar_corrida_prova(row):
        is_race = row["workout_type"] == 1 or "prova" in row["name"].lower()
        if not is_race or row["type"] != "Run":
            return "Não é prova"

        dist = row["distancia_km"]
        if 4.9 <= dist < 5.2:
            return "5k"
        if 9.9 <= dist < 10.2:
            return "10k"
        if 21.0 <= dist < 21.3:
            return "Meia Maratona"
        if 42.0 <= dist < 42.4:
            return "Maratona"
        return "Distância não padrão"

    df["tipo_corrida"] = df.apply(classificar_corrida_prova, axis=1)

    # Categoria de Corrida (Treino, Prova, etc.)
    def classificar_categoria_corrida(row):
        if row["type"] != "Run":
            return "N/A"
        workout_type = row.get("workout_type")
        if workout_type == 1:
            return "Prova"
        if workout_type == 2:
            return "Treino Longo"
        if workout_type == 3:
            return "Treino de Intervalo"
        return "Treino"

    df["categoria_corrida"] = df.apply(classificar_categoria_corrida, axis=1)

    # Garante que a coluna 'gear_id' exista, mesmo que a API não a retorne
    if "gear_id" not in df.columns:
        df["gear_id"] = None

    return df


@st.cache_data
def decodificar_mapa(polyline_string: str | None):
    """Decodifica polyline do Strava em DataFrame para mapa."""
    if not polyline_string:
        return None
    try:
        points = polyline.decode(polyline_string)
        return pd.DataFrame(points, columns=["lat", "lon"])
    except Exception as e:
        print(f"Erro ao decodificar polyline: {e}")
        return None


# -------------------------------------------------------------------
# 4. CAMADA DE UI
# -------------------------------------------------------------------

def exibir_cabecalho(atleta: dict, clima: str, df: pd.DataFrame):
    """Mostra cabeçalho de boas-vindas e KPIs."""
    saudacao = obter_saudacao()
    nome = atleta.get("firstname", "Atleta")
    cidade = atleta.get("city", "N/A")
    estado = atleta.get("state", "N/A")
    foto_url = atleta.get("profile_medium", "")

    col1, col2, col3 = st.columns([1, 2, 3])
    if foto_url:
        col1.image(foto_url, width=110, caption=None)
    col2.title(f"{saudacao}, {nome}!")
    col2.markdown(f"**Localização:** {cidade}, {estado}")
    col2.markdown(f"**Clima atual:** {clima}")

    with col3:
        kpi_col1, kpi_col2 = st.columns(2)
        if not df.empty:
            dist_total = df["distancia_km"].sum()
            tempo_total = df["tempo_horas"].sum()
            elev_total = df["total_elevation_gain"].sum()
            num_atividades = df.shape[0]
            with kpi_col1:
                st.metric("Distância total", f"{dist_total:.1f} km")
                st.metric("Elevação total", f"{elev_total:.0f} m")
            with kpi_col2:
                st.metric("Tempo total", f"{tempo_total:.1f} h")
                st.metric("Nº de atividades", f"{num_atividades}")
        else:
            for col in (kpi_col1, kpi_col2):
                with col:
                    st.metric("Distância total", "0 km")
                    st.metric("Tempo total", "0 h")
    st.write("---")


def exibir_sidebar_filtros(df: pd.DataFrame, mapa_tenis: dict) -> pd.DataFrame:
    """Cria barra lateral de filtros e retorna DF filtrado."""
    st.sidebar.header("Filtros")
    if df.empty:
        st.sidebar.info("Nenhuma atividade para filtrar.")
        return df

    anos_disponiveis = sorted(df["ano"].unique(), reverse=True)
    anos_selecionados = st.sidebar.multiselect(
        "Ano",
        options=anos_disponiveis,
        default=anos_disponiveis,
    )

    tipos_disponiveis = sorted(df["tipo_traduzido"].unique().tolist())
    tipos_selecionados = st.sidebar.multiselect(
        "Tipo de atividade",
        options=tipos_disponiveis,
        default=tipos_disponiveis,
    )

    df_filtrado = df[df["ano"].isin(anos_selecionados) & df["tipo_traduzido"].isin(tipos_selecionados)]

    # Período
    if not df_filtrado.empty:
        st.sidebar.subheader("Período")
        data_max = df_filtrado["data_inicio"].max().date()
        data_min = df_filtrado["data_inicio"].min().date()

        opcoes_periodo = ["Todo o período", "Últimos 90 dias", "Ano atual", "Personalizado"]
        preset = st.sidebar.radio("Atalho de período", options=opcoes_periodo, index=0)

        if preset == "Últimos 90 dias":
            inicio, fim = data_max - timedelta(days=90), data_max
        elif preset == "Ano atual":
            inicio, fim = datetime(data_max.year, 1, 1).date(), data_max
        elif preset == "Todo o período":
            inicio, fim = data_min, data_max
        else:
            inicio, fim = data_min, data_max
            range_input = st.sidebar.date_input(
                "Customizar intervalo",
                value=(data_min, data_max),
                min_value=data_min,
                max_value=data_max,
            )
            if len(range_input) == 2:
                inicio, fim = range_input
        df_filtrado = df_filtrado[df_filtrado["data_inicio"].dt.date.between(inicio, fim)]

    # Filtros específicos de Corrida
    if "Corrida" in tipos_selecionados and not df_filtrado[df_filtrado["type"] == "Run"].empty:
        st.sidebar.subheader("Filtros de corrida")

        categorias_disponiveis = sorted(df_filtrado[df_filtrado["categoria_corrida"] != "N/A"]["categoria_corrida"].unique())
        if categorias_disponiveis:
            categorias_selecionadas = st.sidebar.multiselect(
                "Categoria",
                options=categorias_disponiveis,
                default=categorias_disponiveis,
            )
            if len(categorias_selecionadas) != len(categorias_disponiveis):
                mascara = (df_filtrado["type"] != "Run") | (df_filtrado["categoria_corrida"].isin(categorias_selecionadas))
                df_filtrado = df_filtrado[mascara]

        tenis_ids = df_filtrado[df_filtrado["gear_id"].notna()]["gear_id"].unique()
        mapa_nomes_tenis = {mapa_tenis.get(gear_id, f"Tênis {gear_id}"): gear_id for gear_id in tenis_ids}
        nomes_tenis_disponiveis = sorted(mapa_nomes_tenis.keys())

        if nomes_tenis_disponiveis:
            nomes_selecionados = st.sidebar.multiselect(
                "Tênis utilizado",
                options=nomes_tenis_disponiveis,
                default=nomes_tenis_disponiveis,
            )
            if len(nomes_selecionados) != len(nomes_tenis_disponiveis):
                ids_selecionados = {mapa_nomes_tenis[nome] for nome in nomes_selecionados}
                mascara = (df_filtrado["type"] != "Run") | (df_filtrado["gear_id"].isin(ids_selecionados))
                df_filtrado = df_filtrado[mascara]

    st.sidebar.caption(f"{len(df_filtrado)} atividades após filtros")
    return df_filtrado


def exibir_comparativo_tipos(df: pd.DataFrame):
    """Mostra resumo agrupado por tipo de atividade."""
    if df.empty:
        st.info("Nenhum dado para o comparativo por tipo.")
        return

    st.header("Comparativo por tipo de atividade")
    st.caption("Resumo do desempenho médio e total por tipo de esporte.")
    df_comp = df.groupby("tipo_traduzido", as_index=False).agg(
        total_atividades=("name", "count"),
        distancia_total_km=("distancia_km", "sum"),
        tempo_total_horas=("tempo_horas", "sum"),
        elevacao_total_m=("total_elevation_gain", "sum"),
        vel_media_kmh=("vel_media_kmh", "mean"),
        pace_medio_min_km=("pace_min_km", "mean"),
    ).round(2)

    rename_cols = {
        "tipo_traduzido": "Tipo",
        "total_atividades": "Total de atividades",
        "distancia_total_km": "Distância total (km)",
        "tempo_total_horas": "Tempo total (h)",
        "elevacao_total_m": "Elevação total (m)",
        "vel_media_kmh": "Vel. média (km/h)",
        "pace_medio_min_km": "Pace médio (min/km)",
    }
    df_comp.rename(columns=rename_cols, inplace=True)

    fig = px.bar(
        df_comp.sort_values(by="Distância total (km)", ascending=False),
        x="Distância total (km)",
        y="Tipo",
        orientation="h",
        title="Distância total por tipo de atividade",
        text="Distância total (km)",
    )
    fig.update_traces(texttemplate="%{text:.1f}")
    estilizar_plot(fig)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)


def exibir_comparativo_individual(df: pd.DataFrame):
    """Comparação lado a lado de duas atividades."""
    if df.empty:
        return
    st.header("Comparar duas atividades")
    lista_atividades = df.sort_values(by="data_inicio", ascending=False)["display_name"].tolist()
    if len(lista_atividades) < 2:
        st.info("Selecione pelo menos duas atividades nos filtros para comparar.")
        return

    col_a, col_b = st.columns(2)
    atividade_1_nome = col_a.selectbox("Atividade 1", lista_atividades, index=0)
    atividade_2_nome = col_b.selectbox("Atividade 2", lista_atividades, index=1)
    dados_1 = df[df["display_name"] == atividade_1_nome].iloc[0]
    dados_2 = df[df["display_name"] == atividade_2_nome].iloc[0]

    col_m1, col_m2 = st.columns(2)
    col_m1.markdown(f"**{dados_1['name']}**")
    col_m2.markdown(f"**{dados_2['name']}**")
    col_m1.metric("Distância (km)", f"{dados_1['distancia_km']:.2f}")
    col_m2.metric("Distância (km)", f"{dados_2['distancia_km']:.2f}")
    col_m1.metric("Pace médio", dados_1["pace_formatado"])
    col_m2.metric("Pace médio", dados_2["pace_formatado"])
    col_m1.metric("Tempo (h)", f"{dados_1['tempo_horas']:.2f}")
    col_m2.metric("Tempo (h)", f"{dados_2['tempo_horas']:.2f}")
    col_m1.metric("Elevação (m)", f"{dados_1['total_elevation_gain']:.0f}")
    col_m2.metric("Elevação (m)", f"{dados_2['total_elevation_gain']:.0f}")
    vel_max_1 = (dados_1.get("max_speed", 0) * 3.6).round(2)
    vel_max_2 = (dados_2.get("max_speed", 0) * 3.6).round(2)
    col_m1.metric("Velocidade máx (km/h)", f"{vel_max_1}")
    col_m2.metric("Velocidade máx (km/h)", f"{vel_max_2}")
    fc_1 = dados_1.get("average_heartrate") or "N/A"
    fc_2 = dados_2.get("average_heartrate") or "N/A"
    col_m1.metric("FC média", f"{fc_1}")
    col_m2.metric("FC média", f"{fc_2}")
    col_m1.metric("Kudos", f"{dados_1['kudos_count']}")
    col_m2.metric("Kudos", f"{dados_2['kudos_count']}")


def exibir_detalhes_atividade(df_filtrado: pd.DataFrame, headers: dict, url_base: str):
    """Seção de análise detalhada de uma atividade."""
    if df_filtrado.empty:
        return
    st.header("Análise individual da atividade")
    lista_atividades = df_filtrado.sort_values(by="data_inicio", ascending=False)["display_name"].tolist()
    atividade_nome = st.selectbox("Selecione uma atividade", lista_atividades, index=0, key="detalhe_atividade_select")
    activity_id = df_filtrado.loc[df_filtrado["display_name"] == atividade_nome, "id"].iloc[0]

    with st.spinner(f"Buscando detalhes da atividade '{atividade_nome}'..."):
        detalhes, erro = carregar_detalhes_atividade(activity_id, headers, url_base)
    if erro:
        st.error(f"Não foi possível carregar os detalhes: {erro}")
        return

    st.subheader(f"Resumo: {detalhes.get('name', 'Atividade')}")
    mapa_col, resumo_col = st.columns([1, 1])
    with mapa_col:
        polyline_str = detalhes.get("map", {}).get("polyline", "")
        map_data = decodificar_mapa(polyline_str)
        if map_data is not None and not map_data.empty:
            fig_mapa = px.line_mapbox(map_data, lat="lat", lon="lon", zoom=12, height=500)
            fig_mapa.update_layout(
                mapbox_style="open-street-map",
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
            )
            fig_mapa.update_traces(line=dict(color=PRIMARY_COLOR, width=3))
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            st.info("Nenhum mapa disponível para esta atividade.")
    with resumo_col:
        st.metric("Distância", f"{(detalhes.get('distance', 0) / 1000):.2f} km")
        st.metric("Tempo", f"{(detalhes.get('moving_time', 0) / 3600):.2f} h")
        st.metric("Elevação", f"{detalhes.get('total_elevation_gain', 0)} m")
        st.metric("Calorias", f"{detalhes.get('calories', 0):.0f} kcal")
        pace = df_filtrado.loc[df_filtrado["id"] == activity_id, "pace_formatado"].iloc[0]
        st.metric("Pace médio", pace)

    st.subheader("Análise de ritmo (pace) por quilômetro")
    if detalhes.get("splits_metric"):
        df_splits = pd.DataFrame(detalhes["splits_metric"])
        df_splits["split"] = pd.to_numeric(df_splits["split"])
        df_splits = df_splits.sort_values(by="split", ascending=True)

        def formatar_pace_split(segundos: float) -> str:
            minutos = int(segundos // 60)
            segundos_rest = int(segundos % 60)
            return f"{minutos:02}:{segundos_rest:02}"

        df_splits["pace_min_decimal"] = df_splits["moving_time"] / 60
        df_splits["pace_formatado"] = df_splits["moving_time"].apply(formatar_pace_split)
        df_splits["km"] = df_splits["split"].astype(str)

        col1, col2 = st.columns(2)
        with col1:
            fig_splits_bar = px.bar(
                df_splits,
                x="pace_min_decimal",
                y="km",
                orientation="h",
                title="Pace por KM (barras)",
                text="pace_formatado",
            )
            fig_splits_bar.update_layout(
                yaxis={"autorange": "reversed"},
                xaxis_title="Pace (min/km)",
            )
            fig_splits_bar.update_traces(textfont_size=12, textposition="inside", insidetextanchor="middle")
            estilizar_plot(fig_splits_bar)
            st.plotly_chart(fig_splits_bar, use_container_width=True)
        with col2:
            fig_splits_line = px.line(
                df_splits,
                x="km",
                y="pace_min_decimal",
                title="Curva de ritmo da prova",
                labels={"km": "Quilômetro", "pace_min_decimal": "Pace (min/km)"},
                markers=True,
            )
            fig_splits_line.update_yaxes(autorange="reversed")
            estilizar_plot(fig_splits_line)
            st.plotly_chart(fig_splits_line, use_container_width=True)
    else:
        st.info("Nenhum split métrico (km) encontrado para esta atividade.")

    st.subheader("Desempenho nos segmentos")
    if detalhes.get("segment_efforts"):
        df_segmentos = pd.DataFrame(detalhes["segment_efforts"])
        cols_segmentos = ["name", "distance", "elapsed_time", "pr_rank", "kom_rank"]
        cols_existentes = [c for c in cols_segmentos if c in df_segmentos.columns]
        st.dataframe(df_segmentos[cols_existentes], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum segmento encontrado para esta atividade.")


def exibir_tabela_dados(df: pd.DataFrame):
    """Tabela final com os dados filtrados."""
    st.header("Tabela de dados filtrados")
    if df.empty:
        st.info("Nenhum dado para exibir na tabela.")
        return

    df_display = df.copy()

    rename_cols_table = {
        "name": "Nome",
        "data_inicio": "Data",
        "tipo_traduzido": "Tipo",
        "distancia_km": "Distância (km)",
        "tempo_horas": "Tempo (h)",
        "vel_media_kmh": "Vel. média (km/h)",
        "pace_formatado": "Pace médio",
        "total_elevation_gain": "Elevação (m)",
        "kudos_count": "Kudos",
        "average_heartrate": "FC média",
    }

    cols_to_show = [col for col in rename_cols_table if col in df_display.columns]
    df_display = df_display[cols_to_show]
    df_display.rename(columns=rename_cols_table, inplace=True)

    st.data_editor(
        df_display.sort_values(by="Data", ascending=False),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Data": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
            "Distância (km)": st.column_config.NumberColumn(format="%.2f km"),
            "Tempo (h)": st.column_config.NumberColumn(format="%.2f h"),
            "Vel. média (km/h)": st.column_config.NumberColumn(format="%.2f"),
            "Pace médio": st.column_config.TextColumn(),
            "Elevação (m)": st.column_config.NumberColumn(format="%.0f"),
            "Kudos": st.column_config.NumberColumn(format="%d"),
            "FC média": st.column_config.NumberColumn(format="%.0f"),
        },
    )


# -------------------------------------------------------------------
# 5. MAIN (FLUXO PRINCIPAL)
# -------------------------------------------------------------------

def show_main_dashboard(access_token: str):
    """Função principal que renderiza todo o dashboard."""
    URL_BASE = "https://www.strava.com/api/v3"
    HEADERS = {"Authorization": f"Bearer {access_token}"}

    st.title("Dashboard Strava | Pace de 6")
    st.info(
        "Este dashboard é otimizado para corridas e caminhadas. "
        "Outros tipos de atividades podem não ter todas as métricas detalhadas."
    )

    dados_atleta, erro_atleta = carregar_dados_atleta(f"{URL_BASE}/athlete", HEADERS)
    if erro_atleta or not dados_atleta:
        st.error(erro_atleta or "Erro desconhecido ao carregar atleta.")
        st.stop()

    clima = carregar_clima(dados_atleta.get("city"))

    with st.spinner("Buscando seu histórico de atividades... Pode levar um minuto."):
        df_bruto, erro_ativ = carregar_todas_atividades(f"{URL_BASE}/athlete/activities", HEADERS)
    if erro_ativ or df_bruto is None:
        st.error(erro_ativ or "Erro ao carregar atividades.")
        st.stop()

    df_tratado = tratar_dados(df_bruto)

    # Cria o mapa de tênis a partir dos dados do atleta
    mapa_tenis = {sapato["id"]: sapato["name"] for sapato in dados_atleta.get("shoes", [])}

    df_filtrado = exibir_sidebar_filtros(df_tratado, mapa_tenis)
    exibir_cabecalho(dados_atleta, clima, df_filtrado)

    abas = st.tabs(
        [
            "Visão Geral",
            "Evolução no Tempo",
            "Desempenho Corridas",
            "Análise de Provas",
            "Correlação",
            "Análise Individual",
        ]
    )

    with abas[0]:
        exibir_comparativo_tipos(df_filtrado)
        exibir_comparativo_individual(df_filtrado)
    with abas[1]:
        exibir_evolucao_tempo(df_filtrado)
    with abas[2]:
        exibir_desempenho_corridas(df_filtrado, HEADERS, lambda id, h: carregar_detalhes_atividade(id, h, URL_BASE))
    with abas[3]:
        exibir_evolucao_provas(df_filtrado)
    with abas[4]:
        exibir_correlacao(df_filtrado)
    with abas[5]:
        exibir_detalhes_atividade(df_filtrado, HEADERS, URL_BASE)

    with st.expander("Tabela de dados completa"):
        exibir_tabela_dados(df_filtrado)


if __name__ == "__main__":
    st.error("Execute o arquivo 'login.py' para iniciar a aplicação.")
