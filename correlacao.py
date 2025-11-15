import streamlit as st
import pandas as pd
import plotly.express as px
import requests

@st.cache_data(ttl=86400) # Cache por 1 dia
def get_historical_weather(lat, lon, date):
    """
    Busca a temperatura média para uma data e local específicos usando a API Open-Meteo.
    """
    if lat is None or lon is None:
        return None
        
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "daily": "temperature_2m_mean",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data['daily']['temperature_2m_mean'][0]
    except Exception as e:
        print(f"Erro ao buscar clima histórico: {e}")
        return None

def get_temp_for_row(row):
    latlng = row.get("start_latlng")
    if latlng and isinstance(latlng, list) and len(latlng) == 2:
        return get_historical_weather(latlng[0], latlng[1], row["data_inicio"].strftime("%Y-%m-%d"))
    return None

def exibir_correlacao(df: pd.DataFrame):
    """
    Mostra um heatmap de correlação entre várias métricas de corrida.
    """
    st.write("---")
    st.header("🤔 O que Afeta seu Ritmo?")
    st.write("Este gráfico mostra a correlação entre diferentes variáveis das suas corridas. Valores próximos de 1 (verde) ou -1 (vermelho) indicam uma forte correlação.")

    df_corridas = df[df["type"] == "Run"].copy()

    if df_corridas.empty:
        st.info("Nenhuma corrida encontrada para análise de correlação.")
        return

    # Prepara os dados para correlação
    df_corr = pd.DataFrame()
    df_corr["Distância (km)"] = df_corridas["distancia_km"]
    df_corr["Pace (min/km)"] = df_corridas["pace_min_km"]
    df_corr["FC Média"] = df_corridas["average_heartrate"]
    df_corr["Elevação (m)"] = df_corridas["total_elevation_gain"]
    df_corr["Horário (24h)"] = df_corridas["data_inicio"].dt.hour

    # Busca a temperatura para as corridas (limitado para não sobrecarregar)
    with st.spinner("Buscando dados de temperatura para a análise..."):
        df_corr["Temperatura (°C)"] = df_corridas.apply(get_temp_for_row, axis=1)

    # Limpa dados nulos e calcula a correlação
    df_corr_clean = df_corr.dropna()
    
    if df_corr_clean.shape[0] < 2:
        st.warning("Não há dados suficientes (ou de temperatura) para calcular a correlação.")
        return

    correlation_matrix = df_corr_clean.corr()

    # Gráfico Heatmap
    fig = px.imshow(
        correlation_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='RdYlGn',
        title="Heatmap de Correlação entre Variáveis de Corrida"
    )
    st.plotly_chart(fig, use_container_width=True)
