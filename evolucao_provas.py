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


def exibir_evolucao_provas(df: pd.DataFrame):
    """Mostra a evolução do tempo em provas para distâncias específicas."""
    st.write("---")
    st.header("Evolução em provas")

    df_provas = df[df["tipo_corrida"] != "Não é prova"].copy()

    if df_provas.empty:
        st.info("Nenhuma prova encontrada. Marque suas atividades como 'Prova' ou inclua 'prova' no nome.")
        return

    def formatar_tempo_total(segundos):
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        return f"{h:02}:{m:02}:{s:02}"

    df_provas["tempo_formatado"] = df_provas["tempo_total_segundos"].apply(formatar_tempo_total)

    distancias_disponiveis = sorted(df_provas["tipo_corrida"].unique())
    distancia_selecionada = st.selectbox("Selecione a distância da prova", options=distancias_disponiveis, index=0)

    df_distancia = df_provas[df_provas["tipo_corrida"] == distancia_selecionada].sort_values(by="data_inicio")

    if df_distancia.empty:
        st.warning(f"Nenhuma prova de '{distancia_selecionada}' encontrada.")
        return

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader(f"Evolução do tempo em provas de {distancia_selecionada}")
    with col2:
        with st.popover("Info"):
            st.markdown("Linha descendente indica melhora de tempo na distância selecionada.")

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
            "name": True,
        },
    )

    fig.update_layout(
        xaxis_title="Data da prova",
        yaxis_title="Tempo de conclusão",
        hovermode="x unified",
    )

    fig.update_yaxes(
        tickvals=df_distancia["tempo_total_segundos"],
        ticktext=df_distancia["tempo_formatado"],
    )
    _estilizar(fig)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.subheader("Histórico de provas")
    with col2:
        with st.popover("Info"):
            st.markdown("Dados detalhados de cada prova para a distância selecionada.")

    st.dataframe(
        df_distancia[["data_inicio", "name", "distancia_km", "tempo_formatado", "pace_formatado"]],
        use_container_width=True,
        hide_index=True,
    )
