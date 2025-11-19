import pandas as pd
import plotly.express as px
import streamlit as st

COLORWAY = ["#FF4B4B", "#0ea5e9", "#22c55e", "#f59e0b", "#a855f7"]


def _theme_tokens():
    base = (st.get_option("theme.base") or "light").lower()
    is_dark = base == "dark"
    background = "#0b1221" if is_dark else "#f8fafc"
    font = "#e2e8f0" if is_dark else "#0f172a"
    template = "plotly_dark" if is_dark else "plotly_white"
    return {"background": background, "font": font, "template": template}


def _estilizar(fig):
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


def exibir_evolucao_tempo(df: pd.DataFrame):
    """Mostra a evolução do volume e do tempo de treino ao longo do tempo."""
    st.write("---")
    st.header("Evolução no tempo")

    if df.empty:
        st.info("Nenhum dado disponível para mostrar a evolução no tempo.")
        return

    df_resample = df.set_index("data_inicio").copy()

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Volume semanal (KM)")
    with col2:
        with st.popover("Info"):
            st.markdown("Soma de quilômetros percorridos a cada semana para visualizar consistência e volume.")

    df_semanal = df_resample["distancia_km"].resample("W-Mon").sum().reset_index()
    df_semanal["semana"] = df_semanal["data_inicio"].dt.strftime("%Y-%U")
    fig_vol_sem = px.bar(
        df_semanal,
        x="semana",
        y="distancia_km",
        title="Volume de KM por semana",
        labels={"distancia_km": "Distância (km)", "semana": "Semana"},
        hover_data={"data_inicio": "|%d de %b, %Y"},
    )
    _estilizar(fig_vol_sem)
    st.plotly_chart(fig_vol_sem, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Volume mensal (KM)")
    with col2:
        with st.popover("Info"):
            st.markdown("Total de quilômetros percorridos em cada mês.")

    df_mensal = df_resample["distancia_km"].resample("M").sum().reset_index()
    df_mensal["mes"] = df_mensal["data_inicio"].dt.strftime("%Y-%m")
    fig_vol_mes = px.bar(
        df_mensal,
        x="mes",
        y="distancia_km",
        title="Volume de KM por mês",
        labels={"distancia_km": "Distância (km)", "mes": "Mês"},
    )
    _estilizar(fig_vol_mes)
    st.plotly_chart(fig_vol_mes, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Tempo total de treino por semana (horas)")
    with col2:
        with st.popover("Info"):
            st.markdown("Total de horas treinadas a cada semana.")

    df_tempo_sem = df_resample["tempo_horas"].resample("W-Mon").sum().reset_index()
    df_tempo_sem["semana"] = df_tempo_sem["data_inicio"].dt.strftime("%Y-%U")
    fig_tempo_sem = px.line(
        df_tempo_sem,
        x="semana",
        y="tempo_horas",
        title="Tempo total de treino por semana",
        labels={"tempo_horas": "Tempo (horas)", "semana": "Semana"},
        markers=True,
    )
    _estilizar(fig_tempo_sem)
    st.plotly_chart(fig_tempo_sem, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Número de atividades por mês")
    with col2:
        with st.popover("Info"):
            st.markdown("Frequência de treinos por mês, colorido por tipo de atividade.")

    df_ativ_mes = df_resample.groupby([pd.Grouper(freq="M"), "type"]).size().reset_index(name="count")
    df_ativ_mes["mes"] = df_ativ_mes["data_inicio"].dt.strftime("%Y-%m")
    fig_ativ_mes = px.bar(
        df_ativ_mes,
        x="mes",
        y="count",
        color="type",
        title="Número de atividades por mês",
        labels={"count": "Número de atividades", "mes": "Mês", "type": "Tipo"},
    )
    _estilizar(fig_ativ_mes)
    st.plotly_chart(fig_ativ_mes, use_container_width=True)
