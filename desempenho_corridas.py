import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Funções auxiliares movidas ou adaptadas para este módulo, se necessário
def formatar_pace(pace_decimal: float) -> str:
    if pace_decimal <= 0 or pd.isna(pace_decimal):
        return "N/A"
    minutos = int(pace_decimal)
    segundos = int((pace_decimal * 60) % 60)
    return f"{minutos:02}:{segundos:02}"

def carregar_detalhes_atividade(activity_id: int, headers: dict):
    """
    Função mock ou real para carregar detalhes. 
    Para o exemplo, vamos assumir que ela pode falhar.
    """
    # Esta é uma função de exemplo. A implementação real faria uma chamada de API.
    # from app_strava import carregar_detalhes_atividade as api_call
    # return api_call(activity_id, headers)
    # Por enquanto, retornamos None para não quebrar o código.
    # A função real está no app_strava.py e será passada como argumento.
    return None, "Função de API não implementada neste módulo."


def exibir_desempenho_corridas(df: pd.DataFrame, headers: dict, api_loader):
    """
    Mostra gráficos de análise de desempenho para corridas.
    - api_loader: A função real que carrega os detalhes da atividade.
    """
    st.write("---")
    st.header("🏃‍♀️ Desempenho das Corridas")

    df_corridas = df[df["type"] == "Run"].copy()

    if df_corridas.empty:
        st.info("Nenhuma corrida encontrada nos dados filtrados.")
        return

    # --- 2.1 Pace por Distância (Scatter) ---
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Pace vs. Distância")
    with col2:
        with st.popover("Info"):
            st.markdown("Cada ponto é uma corrida. Ajuda a ver se você é melhor em distâncias curtas ou longas. O eixo Y é invertido (pace mais rápido no topo).")

    fig_scatter_pace_dist = px.scatter(
        df_corridas,
        x="distancia_km",
        y="pace_min_km",
        title="Pace por Distância Percorrida",
        labels={"distancia_km": "Distância (km)", "pace_min_km": "Pace (min/km)"},
        hover_data=["name", "data_inicio"]
    )
    fig_scatter_pace_dist.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_scatter_pace_dist, use_container_width=True)

    # --- 2.2 Velocidade Média ao Longo do Tempo ---
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Velocidade Média ao Longo do Tempo")
    with col2:
        with st.popover("Info"):
            st.markdown("Mostra a evolução da sua velocidade média (em km/h) ao longo do tempo. Uma linha ascendente indica melhora na performance.")

    df_sorted_vel = df_corridas.sort_values("data_inicio")
    fig_line_vel = px.line(
        df_sorted_vel,
        x="data_inicio",
        y="vel_media_kmh",
        title="Evolução da Velocidade Média",
        labels={"data_inicio": "Data", "vel_media_kmh": "Velocidade Média (km/h)"},
        markers=True
    )
    st.plotly_chart(fig_line_vel, use_container_width=True)

    # --- 2.3 Distribuição do Pace ---
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Distribuição do Pace")
    with col2:
        with st.popover("Info"):
            st.markdown("Mostra qual é a sua faixa de pace mais frequente. O pico do histograma indica o ritmo em que você mais corre.")

    fig_hist_pace = px.histogram(
        df_corridas[df_corridas["pace_min_km"] > 0],
        x="pace_min_km",
        nbins=20,
        title="Distribuição de Pace nas Corridas",
        labels={"pace_min_km": "Pace (min/km)"}
    )
    st.plotly_chart(fig_hist_pace, use_container_width=True)

    # --- 2.5 Gráfico de Regressão: Pace x Distância ---
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Regressão Linear: Pace vs. Distância")
    with col2:
        with st.popover("Info"):
            st.markdown("A linha de tendência vermelha mostra como seu pace tende a mudar com o aumento da distância. Se a linha sobe, seu pace piora em distâncias maiores.")

    fig_reg_pace_dist = px.scatter(
        df_corridas[df_corridas["pace_min_km"] > 0],
        x="distancia_km",
        y="pace_min_km",
        title="Tendência do Pace com o Aumento da Distância",
        labels={"distancia_km": "Distância (km)", "pace_min_km": "Pace (min/km)"},
        trendline="ols",
        trendline_color_override="red"
    )
    fig_reg_pace_dist.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_reg_pace_dist, use_container_width=True)

    # --- 2.4 Pace por Quilômetro (Heatmap) ---
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Análise de Quebra (Pace por KM)")
    with col2:
        with st.popover("Info"):
            st.markdown("Analisa o pace em cada quilômetro das suas corridas mais recentes. Cores mais quentes (vermelho/amarelo) indicam um ritmo mais lento, ajudando a identificar em que ponto da corrida você 'quebra'.")

    st.write("Este gráfico analisa o pace em cada quilômetro para entender onde seu ritmo muda.")
    
    corridas_recentes = df_corridas.sort_values("data_inicio", ascending=False).head(15)
    
    all_splits_data = []
    with st.spinner("Buscando dados de splits para o Heatmap..."):
        for index, row in corridas_recentes.iterrows():
            activity_id = row["id"]
            detalhes, erro = api_loader(activity_id, headers)
            
            if erro or not detalhes or "splits_metric" not in detalhes:
                continue

            for split in detalhes["splits_metric"]:
                if split.get("distance", 0) > 990 and split.get("distance", 0) < 1100:
                    all_splits_data.append({
                        "activity_id": activity_id,
                        "display_name": row["display_name"],
                        "km": split["split"],
                        "pace_segundos": split["moving_time"]
                    })

    if not all_splits_data:
        st.warning("Não foi possível encontrar dados de splits (parciais de KM) para as corridas recentes.")
        return

    df_heatmap = pd.DataFrame(all_splits_data)
    df_heatmap["pace_min_km"] = (df_heatmap["pace_segundos"] / 60)
    
    try:
        heatmap_pivot = df_heatmap.pivot_table(
            index="display_name", 
            columns="km", 
            values="pace_min_km"
        )
        
        # A linha abaixo foi removida pois causava o erro. A ordem do heatmap não é crucial.
        # heatmap_pivot = heatmap_pivot.loc[corridas_recentes["display_name"].unique()]

        fig_heatmap = px.imshow(
            heatmap_pivot,
            labels=dict(x="Quilômetro", y="Atividade", color="Pace (min/km)"),
            title="Heatmap de Pace por Quilômetro",
            color_continuous_scale="RdYlGn_r"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o heatmap: {e}")
        st.write("Isso pode acontecer se as atividades selecionadas não tiverem parciais de KM consistentes.")
