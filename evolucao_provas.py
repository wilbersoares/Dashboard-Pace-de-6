import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def exibir_evolucao_provas(df: pd.DataFrame):
    """
    Mostra a evolução do tempo em provas para distâncias específicas.
    """
    st.write("---")
    st.header("🏆 Evolução em Provas")

    df_provas = df[df["tipo_corrida"] != "Não é prova"].copy()

    if df_provas.empty:
        st.info("Nenhuma prova encontrada nos dados filtrados. Marque suas atividades como 'Prova' no Strava ou no nome da atividade.")
        return

    # Formata o tempo para exibição no gráfico (HH:MM:SS)
    def formatar_tempo_total(segundos):
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        return f"{h:02}:{m:02}:{s:02}"

    df_provas["tempo_formatado"] = df_provas["tempo_total_segundos"].apply(formatar_tempo_total)

    # Seletor de distância
    distancias_disponiveis = sorted(df_provas["tipo_corrida"].unique())
    distancia_selecionada = st.selectbox(
        "Selecione a distância da prova:",
        options=distancias_disponiveis,
        index=0
    )

    df_distancia = df_provas[df_provas["tipo_corrida"] == distancia_selecionada].sort_values(by="data_inicio")

    if df_distancia.empty:
        st.warning(f"Nenhuma prova de '{distancia_selecionada}' encontrada.")
        return
    
    # Gráfico de Linha da Evolução
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader(f"Evolução do Tempo em Provas de {distancia_selecionada}")
    with col2:
        with st.popover("Info"):
            st.markdown("Acompanhe seu progresso em provas de uma distância específica. Uma linha descendente indica que você está ficando mais rápido.")

    fig = px.line(
        df_distancia,
        x="data_inicio",
        y="tempo_total_segundos",
        title=f"Seus tempos em provas de {distancia_selecionada}",
        markers=True,
        hover_data={
            "data_inicio": "|%d de %b, %Y",
            "tempo_total_segundos": False,
            "tempo_formatado": True,
            "name": True
        }
    )

    # Formata o eixo Y para mostrar o tempo no formato HH:MM:SS
    fig.update_layout(
        xaxis_title="Data da Prova",
        yaxis_title="Tempo de Conclusão",
        hovermode="x unified"
    )
    
    # Oculta os valores numéricos do eixo Y e usa os textos formatados
    fig.update_yaxes(
        tickvals=df_distancia["tempo_total_segundos"],
        ticktext=df_distancia["tempo_formatado"]
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabela de dados das provas
    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Histórico de Provas")
    with col2:
        with st.popover("Info"):
            st.markdown("Tabela com os dados detalhados de cada prova para a distância selecionada.")
            
    st.dataframe(
        df_distancia[["data_inicio", "name", "distancia_km", "tempo_formatado", "pace_formatado"]],
        use_container_width=True,
        hide_index=True
    )