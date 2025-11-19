import numpy as np
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


def formatar_pace(pace_decimal: float) -> str:
    if pace_decimal <= 0 or pd.isna(pace_decimal):
        return "N/A"
    minutos = int(pace_decimal)
    segundos = int((pace_decimal * 60) % 60)
    return f"{minutos:02}:{segundos:02}"


def exibir_desempenho_corridas(df: pd.DataFrame, headers: dict, api_loader):
    """
    Mostra gráficos de análise de desempenho para corridas.
    - api_loader: função que carrega detalhes da atividade.
    """
    st.write("---")
    st.header("Desempenho das corridas")

    df_corridas = df[df["type"] == "Run"].copy()

    if df_corridas.empty:
        st.info("Nenhuma corrida encontrada nos dados filtrados.")
        return

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Pace vs. distância")
    with col2:
        with st.popover("Info"):
            st.markdown("Cada ponto é uma corrida. Eixo Y invertido (pace mais rápido no topo).")

    fig_scatter_pace_dist = px.scatter(
        df_corridas,
        x="distancia_km",
        y="pace_min_km",
        title="Pace por distância percorrida",
        labels={"distancia_km": "Distância (km)", "pace_min_km": "Pace (min/km)"},
        hover_data=["name", "data_inicio"],
    )
    fig_scatter_pace_dist.update_yaxes(autorange="reversed")
    _estilizar(fig_scatter_pace_dist)
    st.plotly_chart(fig_scatter_pace_dist, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Velocidade média ao longo do tempo")
    with col2:
        with st.popover("Info"):
            st.markdown("Linha ascendente indica melhora de performance.")

    df_sorted_vel = df_corridas.sort_values("data_inicio")
    fig_line_vel = px.line(
        df_sorted_vel,
        x="data_inicio",
        y="vel_media_kmh",
        title="Evolução da velocidade média",
        labels={"data_inicio": "Data", "vel_media_kmh": "Velocidade média (km/h)"},
        markers=True,
    )
    _estilizar(fig_line_vel)
    st.plotly_chart(fig_line_vel, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Distribuição do pace")
    with col2:
        with st.popover("Info"):
            st.markdown("Mostra a faixa de pace mais frequente nas corridas.")

    fig_hist_pace = px.histogram(
        df_corridas[df_corridas["pace_min_km"] > 0],
        x="pace_min_km",
        nbins=20,
        title="Distribuição de pace nas corridas",
        labels={"pace_min_km": "Pace (min/km)"},
    )
    _estilizar(fig_hist_pace)
    st.plotly_chart(fig_hist_pace, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Regressão: pace x distância")
    with col2:
        with st.popover("Info"):
            st.markdown("Linha de tendência mostra como o pace varia com a distância.")

    fig_reg_pace_dist = px.scatter(
        df_corridas[df_corridas["pace_min_km"] > 0],
        x="distancia_km",
        y="pace_min_km",
        title="Tendência do pace com aumento da distância",
        labels={"distancia_km": "Distância (km)", "pace_min_km": "Pace (min/km)"},
        trendline="ols",
        trendline_color_override="red",
    )
    fig_reg_pace_dist.update_yaxes(autorange="reversed")
    _estilizar(fig_reg_pace_dist)
    st.plotly_chart(fig_reg_pace_dist, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Análise de quebra (pace por km)")
    with col2:
        with st.popover("Info"):
            st.markdown("Identifica em que km o ritmo cai nas corridas recentes.")

    st.write("Gráfico analisa o pace em cada quilômetro das corridas mais recentes.")

    corridas_recentes = df_corridas.sort_values("data_inicio", ascending=False).head(12)

    all_splits_data = []
    with st.spinner("Buscando dados de splits para o heatmap..."):
        for _, row in corridas_recentes.iterrows():
            activity_id = row["id"]
            detalhes, erro = api_loader(activity_id, headers)

            if erro or not detalhes or "splits_metric" not in detalhes:
                continue

            for split in detalhes["splits_metric"]:
                if 990 < split.get("distance", 0) < 1100:
                    all_splits_data.append(
                        {
                            "activity_id": activity_id,
                            "display_name": row["display_name"],
                            "km": split["split"],
                            "pace_segundos": split["moving_time"],
                        }
                    )

    if not all_splits_data:
        st.warning("Não foi possível encontrar dados de splits para as corridas recentes.")
        return

    df_heatmap = pd.DataFrame(all_splits_data)
    df_heatmap["pace_min_km"] = df_heatmap["pace_segundos"] / 60

    heatmap_pivot = df_heatmap.pivot_table(index="display_name", columns="km", values="pace_min_km")
    heatmap_pivot = heatmap_pivot.sort_index(ascending=False)

    fig_heatmap = px.imshow(
        heatmap_pivot,
        labels=dict(x="Quilômetro", y="Atividade", color="Pace (min/km)"),
        title="Heatmap de pace por quilômetro",
        color_continuous_scale="RdYlGn_r",
    )
    tokens = _theme_tokens()
    fig_heatmap.update_layout(
        plot_bgcolor=tokens["background"],
        paper_bgcolor=tokens["background"],
        font=dict(color=tokens["font"], size=13),
        margin=dict(l=0, r=0, t=50, b=30),
        template=tokens["template"],
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
