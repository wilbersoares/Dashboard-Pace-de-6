import streamlit as st
import pandas as pd
import plotly.express as px

def exibir_evolucao_tempo(df: pd.DataFrame):
    """
    Mostra a evolução do volume e tempo de treino ao longo do tempo.
    """
    st.write("---")
    st.header("📈 Evolução no Tempo")

    if df.empty:
        st.info("Nenhum dado disponível para mostrar a evolução no tempo.")
        return

    # Prepara o DataFrame para resampling
    df_resample = df.set_index("data_inicio").copy()

    # 1.1 Volume Semanal (KM por semana)
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Volume Semanal (KM)")
    with col2:
        with st.popover("Info"):
            st.markdown("Mostra a soma de quilômetros percorridos a cada semana, ajudando a visualizar a consistência e o volume do seu treino semanal.")
    
    df_semanal = df_resample["distancia_km"].resample("W-Mon").sum().reset_index()
    df_semanal["semana"] = df_semanal["data_inicio"].dt.strftime("%Y-%U")
    fig_vol_sem = px.bar(
        df_semanal,
        x="semana",
        y="distancia_km",
        title="Volume de KM por Semana",
        labels={"distancia_km": "Distância (km)", "semana": "Semana"},
        hover_data={"data_inicio": "|%d de %b, %Y"}
    )
    st.plotly_chart(fig_vol_sem, use_container_width=True)

    # 1.2 Volume Mensal (KM/mês)
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Volume Mensal (KM)")
    with col2:
        with st.popover("Info"):
            st.markdown("Compara o total de quilômetros percorridos em cada mês, ideal para análises de macrociclos de treino.")
            
    df_mensal = df_resample["distancia_km"].resample("M").sum().reset_index()
    df_mensal["mes"] = df_mensal["data_inicio"].dt.strftime("%Y-%m")
    fig_vol_mes = px.bar(
        df_mensal,
        x="mes",
        y="distancia_km",
        title="Volume de KM por Mês",
        labels={"distancia_km": "Distância (km)", "mes": "Mês"},
    )
    st.plotly_chart(fig_vol_mes, use_container_width=True)

    # 1.3 Tempo total de treino por semana
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Tempo Total de Treino por Semana (horas)")
    with col2:
        with st.popover("Info"):
            st.markdown("Indica o total de horas que você treinou a cada semana. É um bom indicador de dedicação e intensidade.")

    df_tempo_sem = df_resample["tempo_horas"].resample("W-Mon").sum().reset_index()
    df_tempo_sem["semana"] = df_tempo_sem["data_inicio"].dt.strftime("%Y-%U")
    fig_tempo_sem = px.line(
        df_tempo_sem,
        x="semana",
        y="tempo_horas",
        title="Tempo Total de Treino por Semana",
        labels={"tempo_horas": "Tempo (horas)", "semana": "Semana"},
        markers=True
    )
    st.plotly_chart(fig_tempo_sem, use_container_width=True)

    # 1.4 Número de atividades por mês
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Número de Atividades por Mês")
    with col2:
        with st.popover("Info"):
            st.markdown("Mostra a frequência de treinos por mês, com cores divididas por tipo de atividade, ajudando a ver a variedade dos seus treinos.")

    df_ativ_mes = df_resample.groupby([pd.Grouper(freq='M'), "type"]).size().reset_index(name="count")
    df_ativ_mes["mes"] = df_ativ_mes["data_inicio"].dt.strftime("%Y-%m")
    fig_ativ_mes = px.bar(
        df_ativ_mes,
        x="mes",
        y="count",
        color="type",
        title="Número de Atividades por Mês",
        labels={"count": "Número de Atividades", "mes": "Mês", "type": "Tipo"},
    )
    st.plotly_chart(fig_ativ_mes, use_container_width=True)
