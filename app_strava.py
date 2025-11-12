import streamlit as st
import requests
import pandas as pd

# --- 1. CONFIGURAÇÃO INICIAL E BUSCA DE DADOS ---

# Configura o layout da página
st.set_page_config(page_title="Dashboard Strava", layout="wide")
st.title("Dashboard de Atividades PACE DE 6 🚴‍♂️🏃‍♂️")

# Busca o token do arquivo .streamlit/secrets.toml
try:
    BEARER_TOKEN = st.secrets["BEARER_TOKEN"]
    HEADERS = {'Authorization': f'Bearer {BEARER_TOKEN}'}
    URL_BASE = "https://www.strava.com/api/v3"
except FileNotFoundError:
    st.error("Arquivo 'secrets.toml' não encontrado. Crie-o na pasta .streamlit/")
    st.stop()


# --- 2. FUNÇÕES DO APLICATIVO ---

# FUNÇÃO CORRIGIDA: Removemos todos os st.toast, st.error, etc.
@st.cache_data(ttl=3600)  # Armazena os dados em cache por 1 hora
def carregar_todas_atividades(url, headers):
    """
    Busca TODAS as atividades do atleta, página por página.
    Retorna uma tupla: (DataFrame, ErrorMessage)
    Se sucesso, retorna (df, None)
    Se erro, retorna (None, "Mensagem de erro")
    """
    todas_atividades = []
    pagina = 1
    per_page = 100  # Máximo permitido pelo Strava
    
    while True:
        try:
            params = {'page': pagina, 'per_page': per_page}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                # Em vez de st.error, retorna a mensagem de erro
                erro_msg = f"Erro na API (Página {pagina}): {response.status_code} - {response.text}"
                return None, erro_msg

            dados_pagina = response.json()
            
            if not dados_pagina:
                break # Sucesso, terminou de buscar
                
            todas_atividades.extend(dados_pagina)
            pagina += 1

        except Exception as e:
            erro_msg = f"Ocorreu um erro na requisição (Página {pagina}): {e}"
            return None, erro_msg
    
    if not todas_atividades:
        return None, "Nenhuma atividade encontrada."
        
    df = pd.DataFrame(todas_atividades)
    return df, None # Sucesso, retorna o DataFrame e nenhum erro


@st.cache_data
def tratar_dados(df_bruto):
    """
    Aplica todas as transformações de dados em um só lugar.
    """
    df = df_bruto.copy()
    
    # 1. Conversões
    df['distancia_km'] = (df['distance'] / 1000).round(2)
    df['tempo_horas'] = (df['moving_time'] / 3600).round(2)
    df['vel_media_kmh'] = (df['average_speed'] * 3.6).round(2)
    
    # 2. Cálculo de Pace
    df['pace_min_km'] = 0.0
    # Usamos .loc para evitar avisos do Pandas
    df.loc[df['vel_media_kmh'] > 0, 'pace_min_km'] = 60 / df.loc[df['vel_media_kmh'] > 0, 'vel_media_kmh']
    
    # 3. Formatação de Pace
    def formatar_pace(pace_decimal):
        if pace_decimal <= 0:
            return "N/A"
        minutos = int(pace_decimal)
        segundos = int((pace_decimal * 60) % 60)
        return f"{minutos:02}:{segundos:02} min/km"
        
    df['pace_formatado'] = df['pace_min_km'].apply(formatar_pace)

    # 4. Tratamento de Datas
    df['data_inicio'] = pd.to_datetime(df['start_date_local'])
    df['ano'] = df['data_inicio'].dt.year
    
    # 5. Nome de Exibição
    df['display_name'] = df['data_inicio'].dt.strftime('%Y-%m-%d') + ' | ' + df['name']
    
    return df


def exibir_sidebar_filtros(df):
    """
    Cria a barra lateral e retorna o DataFrame filtrado.
    """
    st.sidebar.header("Filtros 📊")
    
    # Filtro de Ano
    anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
    anos_selecionados = st.sidebar.multiselect(
        "Selecione o Ano:",
        options=anos_disponiveis,
        default=anos_disponiveis,
        key="filtro_ano"
    )
    
    # Filtro de Tipo de Atividade
    tipos_disponiveis = df['type'].unique().tolist()
    tipos_selecionados = st.sidebar.multiselect(
        "Selecione o Tipo de Atividade:",
        options=tipos_disponiveis,
        default=tipos_disponiveis,
        key="filtro_tipo"
    )
    
    # Retorna o DataFrame já filtrado
    return df[
        (df['ano'].isin(anos_selecionados)) &
        (df['type'].isin(tipos_selecionados))
    ]


def exibir_kpis(df):
    """
    Mostra os KPIs principais em colunas.
    """
    st.header("Seus KPIs Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    dist_total = df['distancia_km'].sum()
    col1.metric("Distância Total", f"{dist_total:.2f} km")
    
    tempo_total = df['tempo_horas'].sum()
    col2.metric("Tempo Total", f"{tempo_total:.2f} h")
    
    elev_total = df['total_elevation_gain'].sum()
    col3.metric("Elevação Total", f"{elev_total} m")
    
    num_atividades = df.shape[0]
    col4.metric("Total de Atividades", f"{num_atividades}")


def exibir_comparativo_tipos(df):
    """
    Mostra a tabela de resumo agrupada por tipo de atividade.
    """
    st.header("Comparativo por Tipo de Atividade")
    st.write("Um resumo do seu desempenho médio e total para cada tipo de esporte.")
    
    df_comparativo = df.groupby('type').agg(
        total_atividades=('name', 'count'),
        distancia_total_km=('distancia_km', 'sum'),
        tempo_total_horas=('tempo_horas', 'sum'),
        elevacao_total_m=('total_elevation_gain', 'sum'),
        vel_media_kmh=('vel_media_kmh', 'mean'),
        pace_medio_min_km=('pace_min_km', 'mean')
    ).round(2)
    
    st.dataframe(df_comparativo)


def exibir_comparativo_individual(df):
    """
    Mostra os seletores e as métricas para comparar duas atividades.
    """
    st.header("Comparar Duas Atividades Específicas 🥊")
    st.write("Selecione duas atividades da lista (baseada nos seus filtros) para um 'head-to-head'.")
    
    # Ordena a lista de atividades para mostrar as mais recentes primeiro
    lista_atividades = df.sort_values(by='data_inicio', ascending=False)['display_name'].tolist()
    
    col_a, col_b = st.columns(2)
    
    atividade_1_nome = col_a.selectbox(
        "Selecione a Atividade 1:",
        lista_atividades,
        index=0,
        key="comp_ativ_1"
    )
    
    atividade_2_nome = col_b.selectbox(
        "Selecione a Atividade 2:",
        lista_atividades,
        index=1 if len(lista_atividades) > 1 else 0,
        key="comp_ativ_2"
    )
    
    # Pega os dados completos das atividades selecionadas
    dados_1 = df[df['display_name'] == atividade_1_nome].iloc[0]
    dados_2 = df[df['display_name'] == atividade_2_nome].iloc[0]
    
    # Cria colunas para mostrar os resultados lado a lado
    col_metrica1, col_metrica2 = st.columns(2)
    
    # Mostra as métricas
    col_metrica1.metric("Distância (km)", f"{dados_1['distancia_km']:.2f}")
    col_metrica2.metric("Distância (km)", f"{dados_2['distancia_km']:.2f}")

    col_metrica1.metric("Velocidade Média (km/h)", f"{dados_1['vel_media_kmh']:.2f}")
    col_metrica2.metric("Velocidade Média (km/h)", f"{dados_2['vel_media_kmh']:.2f}")
    
    col_metrica1.metric("Pace Médio", f"{dados_1['pace_formatado']}")
    col_metrica2.metric("Pace Médio", f"{dados_2['pace_formatado']}")

    col_metrica1.metric("Tempo (horas)", f"{dados_1['tempo_horas']:.2f}")
    col_metrica2.metric("Tempo (horas)", f"{dados_2['tempo_horas']:.2f}")

    col_metrica1.metric("Elevação (m)", f"{dados_1['total_elevation_gain']:.2f}")
    col_metrica2.metric("Elevação (m)", f"{dados_2['total_elevation_gain']:.2f}")

    col_metrica1.metric("Kudos 👍", f"{dados_1['kudos_count']}")
    col_metrica2.metric("Kudos 👍", f"{dados_2['kudos_count']}")


def exibir_tabela_dados(df):
    """
    Mostra a tabela de dados filtrados no final.
    """
    st.write("---")
    st.header("Tabela de Dados Filtrados")
    
    colunas_uteis = [
        'name', 'data_inicio', 'type', 'distancia_km', 'tempo_horas', 
        'vel_media_kmh', 'pace_formatado', 'total_elevation_gain', 'kudos_count'
    ]
    
    st.data_editor(
        df[colunas_uteis].sort_values(by='data_inicio', ascending=False), # Ordena por data
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )

# --- 3. CORPO PRINCIPAL DO APP (LÓGICA DE EXECUÇÃO) ---

# Mostra um "spinner" (loading) enquanto a função cacheada roda
with st.spinner("Buscando dados do Strava... Isso pode levar um minuto se for a primeira vez."):
    df_bruto, erro = carregar_todas_atividades(f"{URL_BASE}/athlete/activities", HEADERS)

# Agora, checamos o resultado FORA da função cacheada
if erro:
    st.error(erro) # Mostra o erro que a função retornou
    st.stop() # Para a execução do app
elif df_bruto is None:
     st.warning("Nenhuma atividade encontrada.")
     st.stop()
else:
    # Se deu tudo certo, exibe o sucesso
    st.success(f"Total de {df_bruto.shape[0]} atividades carregadas!")

# O resto do app só roda se os dados existirem
try:
    df_tratado = tratar_dados(df_bruto)
    df_filtrado = exibir_sidebar_filtros(df_tratado)
    
    if df_filtrado.empty:
        st.warning("Nenhuma atividade encontrada com os filtros selecionados.")
    else:
        # Exibe todos os módulos do dashboard
        exibir_kpis(df_filtrado)
        
        st.write("---")
        exibir_comparativo_tipos(df_filtrado)
        
        st.write("---")
        exibir_comparativo_individual(df_filtrado)
        
        exibir_tabela_dados(df_filtrado)
except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}")