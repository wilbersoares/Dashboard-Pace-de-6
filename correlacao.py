import pandas as pd
import plotly.express as px
import requests
import streamlit as st

COLORWAY = ["#FF4B4B", "#0ea5e9", "#22c55e", "#f59e0b", "#a855f7"]


def _theme_tokens():
    base = (st.get_option("theme.base") or "light").lower()
    is_dark = base == "dark"
    background = "#0b1221" if is_dark else "#f8fafc"
    font = "#e2e8f0" if is_dark else "#0f172a"
    template = "plotly_dark" if is_dark else "plotly_white"
    return {"background": background, "font": font, "template": template}


@st.cache_data(ttl=86400)  # Cache por 1 dia
def get_historical_weather(lat, lon, date):
    """Busca a temperatura média para uma data e local específicos usando a API Open-Meteo."""
    if lat is None or lon is None:
        return None

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "daily": "temperature_2m_mean",
        "timezone": "auto",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["daily"]["temperature_2m_mean"][0]
    except Exception as e:
        print(f"Erro ao buscar clima histórico: {e}")
        return None


def get_temp_for_row(row):
    latlng = row.get("start_latlng")
    if latlng and isinstance(latlng, list) and len(latlng) == 2:
        return get_historical_weather(latlng[0], latlng[1], row["data_inicio"].strftime("%Y-%m-%d"))
    return None


def exibir_correlacao(df: pd.DataFrame):
    """Mostra um heatmap de correlação entre várias métricas de corrida."""
    st.write("---")
    st.header("O que afeta seu ritmo?")
    st.write(
        "Valores próximos de 1 (verde) ou -1 (vermelho) indicam uma correlação forte positiva ou negativa entre as variáveis."
    )

    df_corridas = df[df["type"] == "Run"].copy()

    if df_corridas.empty:
        st.info("Nenhuma corrida encontrada para análise de correlação.")
        return

    df_corr = pd.DataFrame()
    df_corr["Distância (km)"] = df_corridas["distancia_km"]
    df_corr["Pace (min/km)"] = df_corridas["pace_min_km"]
    df_corr["FC média"] = df_corridas["average_heartrate"]
    df_corr["Elevação (m)"] = df_corridas["total_elevation_gain"]
    df_corr["Horário (24h)"] = df_corridas["data_inicio"].dt.hour

    with st.spinner("Buscando dados de temperatura para a análise..."):
        df_corr["Temperatura (°C)"] = df_corridas.apply(get_temp_for_row, axis=1)

    df_corr_clean = df_corr.dropna()

    if df_corr_clean.shape[0] < 2:
        st.warning("Não há dados suficientes (ou de temperatura) para calcular a correlação.")
        return

    correlation_matrix = df_corr_clean.corr()

    fig = px.imshow(
        correlation_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdYlGn",
        title="Heatmap de correlação entre variáveis de corrida",
    )
    tokens = _theme_tokens()
    fig.update_layout(
        plot_bgcolor=tokens["background"],
        paper_bgcolor=tokens["background"],
        font=dict(color=tokens["font"], size=13),
        margin=dict(l=0, r=0, t=50, b=30),
        template=tokens["template"],
    )
    st.plotly_chart(fig, use_container_width=True)
