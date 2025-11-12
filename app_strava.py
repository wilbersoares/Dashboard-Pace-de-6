import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote  # Para tratar nomes de cidades com acentos
import plotly.express as px  # Para gráficos interativos (mapa e barras)
import polyline             # Para decodificar os mapas do Strava

# --- 1. CONFIGURAÇÃO INICIAL ---

# Configura o layout da página
st.set_page_config(page_title="Dashboard Strava", layout="wide", initial_sidebar_state="expanded")

# Busca o token do arquivo .streamlit/secrets.toml
try:
    BEARER_TOKEN = st.secrets["BEARER_TOKEN"]
    HEADERS = {'Authorization': f'Bearer {BEARER_TOKEN}'}
    URL_BASE = "https://www.strava.com/api/v3"
except FileNotFoundError:
    st.error("Arquivo 'secrets.toml' não encontrado. Crie-o na pasta .streamlit/")
    st.stop()
except KeyError:
    st.error("Chave 'BEARER_TOKEN' não encontrada no 'secrets.toml'. Verifique seu arquivo.")
    st.stop()


# --- 2. FUNÇÕES DE BUSCA DE DADOS (APIs) ---

@st.cache_data(ttl=86400)  # Cache de 1 dia para dados do atleta
def carregar_dados_atleta(url, headers):
    """
    Busca os dados do perfil do atleta (GET /athlete).
    """
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Erro ao buscar dados do atleta: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"Erro na conexão com /athlete: {e}"

@st.cache_data(ttl=900)  # Cache de 15 minutos para o clima
def carregar_clima(cidade):
    """
    Busca o clima atual da cidade usando a API gratuita wttr.in.
    """
    if not cidade:
        return "Clima (cidade não informada)"
    try:
        cidade_url = quote(cidade) # Codifica caracteres especiais (ex: Cuiabá -> Cuiab%C3%A1)
        url_clima = f"https://wttr.in/{cidade_url}?format=j1"
        
        response = requests.get(url_clima, timeout=5) # Timeout de 5s
        
        if response.status_code == 200:
            dados = response.json()
            
            # Parse mais robusto para evitar erros
            condition = dados.get('current_condition', [{}])[0]
            temp_c = condition.get('temp_C')
            lang_pt = condition.get('lang_pt', [{}])[0]
            desc = lang_pt.get('value')
            
            if temp_c and desc:
                return f"{temp_c}°C, {desc}"
            elif temp_c:
                return f"{temp_c}°C" # Fallback se a descrição falhar
            else:
                return "Dados de clima incompletos"
        else:
            return f"Clima indisponível ({response.status_code})"
    except Exception as e:
        # Loga o erro no console do terminal para debugarmos
        print(f"ERRO AO BUSCAR CLIMA: {e}") 
        return "Clima indisponível (Erro de conexão)"

@st.cache_data(ttl=3600)  # Cache de 1 hora para as atividades
def carregar_todas_atividades(url, headers):
    """
    Busca TODAS as atividades do atleta, página por página.
    Retorna uma tupla: (DataFrame, ErrorMessage)
    """
    todas_atividades = []
    pagina = 1
    per_page = 100  # Máximo permitido pelo Strava

    while True:
        try:
            params = {'page': pagina, 'per_page': per_page}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
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
    return df, None # Sucesso

@st.cache_data(ttl=3600)
def carregar_detalhes_atividade(activity_id, headers):
    """
    Busca os detalhes completos de UMA atividade (splits, segmentos, mapa).
    """
    url = f"{URL_BASE}/activities/{activity_id}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Erro ao buscar detalhes da atividade: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"Erro na conexão com /activities/{activity_id}: {e}"


# --- 3. FUNÇÕES DE LÓGICA E TRATAMENTO ---

def obter_saudacao():
    """
    Verifica a hora local do servidor e retorna a saudação correta.
    """
    agora = datetime.now().hour
    if 5 <= agora < 12:
        return "Bom dia"
    elif 12 <= agora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

@st.cache_data
def tratar_dados(df_bruto):
    """
    Aplica todas as transformações de dados das atividades.
    """
    df = df_bruto.copy()
    
    # Colunas que podem não existir (ex: atividades indoor)
    if 'distance' not in df.columns: df['distance'] = 0
    if 'moving_time' not in df.columns: df['moving_time'] = 0
    if 'average_speed' not in df.columns: df['average_speed'] = 0
    if 'total_elevation_gain' not in df.columns: df['total_elevation_gain'] = 0
    if 'kudos_count' not in df.columns: df['kudos_count'] = 0
    if 'average_heartrate' not in df.columns: df['average_heartrate'] = 0
    if 'max_speed' not in df.columns: df['max_speed'] = 0
    if 'average_watts' not in df.columns: df['average_watts'] = 0

    df['distancia_km'] = (df['distance'] / 1000).round(2)
    df['tempo_horas'] = (df['moving_time'] / 3600).round(2)
    df['vel_media_kmh'] = (df['average_speed'] * 3.6).round(2)
    
    df['pace_min_km'] = 0.0
    df.loc[df['vel_media_kmh'] > 0, 'pace_min_km'] = 60 / df.loc[df['vel_media_kmh'] > 0, 'vel_media_kmh']
    
    def formatar_pace(pace_decimal):
        if pace_decimal <= 0:
            return "N/A"
        minutos = int(pace_decimal)
        segundos = int((pace_decimal * 60) % 60)
        return f"{minutos:02}:{segundos:02} min/km"
        
    df['pace_formatado'] = df['pace_min_km'].apply(formatar_pace)

    df['data_inicio'] = pd.to_datetime(df['start_date_local'])
    df['ano'] = df['data_inicio'].dt.year
    df['display_name'] = df['data_inicio'].dt.strftime('%Y-%m-%d') + ' | ' + df['name']
    
    return df

@st.cache_data
def decodificar_mapa(polyline_string):
    """
    Decodifica uma string polyline do Strava em um DataFrame para o st.map().
    """
    if not polyline_string:
        return None
    try:
        # Decodifica a string em uma lista de tuplas (lat, lon)
        points = polyline.decode(polyline_string)
        
        # st.map() precisa de um DataFrame com colunas 'lat' e 'lon'
        df_mapa = pd.DataFrame(points, columns=['lat', 'lon'])
        return df_mapa
    except Exception as e:
        print(f"Erro ao decodificar polyline: {e}")
        return None


# --- 4. FUNÇÕES DE VISUALIZAÇÃO (O DASHBOARD) ---

def exibir_cabecalho(atleta, clima, df):
    """
    Mostra o cabeçalho de boas-vindas E os KPIs filtrados.
    """
    saudacao = obter_saudacao()
    nome = atleta.get('firstname', 'Atleta')
    cidade = atleta.get('city', 'N/A')
    estado = atleta.get('state', 'N/A')
    foto_url = atleta.get('profile_medium', '') # URL da foto de perfil
    
    # Layout: [Foto | Boas-vindas | KPIs]
    col1, col2, col3 = st.columns([1, 2, 2]) # 1 para foto, 2 para texto, 2 para KPIs
    
    # --- Coluna 1: Foto ---
    if foto_url:
        # Imagem reduzida (width=90) e correção do warning
        col1.image(foto_url, width=90, use_container_width=True, output_format="PNG") 
    
    # --- Coluna 2: Boas-vindas ---
    col2.title(f"{saudacao}, {nome}!")
    col2.markdown(f"**Localização:** {cidade}, {estado}")
    col2.markdown(f"**Clima Atual:** {clima}")
    
    # --- Coluna 3: KPIs (Movidos para cá) ---
    with col3:
        # Criamos um grid 2x2 para os KPIs
        kpi_col1, kpi_col2 = st.columns(2)
        
        # Verifica se o dataframe está vazio antes de calcular
        if not df.empty:
            dist_total = df['distancia_km'].sum()
            kpi_col1.metric("Distância Total", f"{dist_total:.2f} km")
            
            tempo_total = df['tempo_horas'].sum()
            kpi_col2.metric("Tempo Total", f"{tempo_total:.2f} h")
            
            elev_total = df['total_elevation_gain'].sum()
            kpi_col1.metric("Elevação Total", f"{elev_total} m")
            
            num_atividades = df.shape[0]
            kpi_col2.metric("Total de Atividades", f"{num_atividades}")
        else:
            # Mostra KPIs zerados se não houver dados
            kpi_col1.metric("Distância Total", "0.00 km")
            kpi_col2.metric("Tempo Total", "0.00 h")
            kpi_col1.metric("Elevação Total", "0 m")
            kpi_col2.metric("Total de Atividades", "0")

    st.write("---") # Linha divisória


def exibir_sidebar_filtros(df):
    """
    Cria a barra lateral e retorna o DataFrame filtrado.
    """
    st.sidebar.header("Filtros 📊")
    
    anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
    anos_selecionados = st.sidebar.multiselect(
        "Selecione o Ano:", options=anos_disponiveis, default=anos_disponiveis, key="filtro_ano"
    )
    
    tipos_disponiveis = df['type'].unique().tolist()
    tipos_selecionados = st.sidebar.multiselect(
        "Selecione o Tipo de Atividade:", options=tipos_disponiveis, default=tipos_disponiveis, key="filtro_tipo"
    )
    
    return df[
        (df['ano'].isin(anos_selecionados)) &
        (df['type'].isin(tipos_selecionados))
    ]


def exibir_comparativo_tipos(df):
    """
    Mostra a tabela de resumo agrupada por tipo de atividade.
    """
    st.header("Comparativo por Tipo de Atividade")
    st.write("Um resumo do seu desempenho médio e total para cada tipo de esporte.")
    
    df_comparativo = df.groupby('type', as_index=False).agg(
        total_atividades=('name', 'count'),
        distancia_total_km=('distancia_km', 'sum'),
        tempo_total_horas=('tempo_horas', 'sum'),
        elevacao_total_m=('total_elevation_gain', 'sum'),
        vel_media_kmh=('vel_media_kmh', 'mean'),
        pace_medio_min_km=('pace_min_km', 'mean')
    ).round(2)
    
    # Usa Plotly para o gráfico de barras
    fig = px.bar(
        df_comparativo.sort_values(by='distancia_total_km', ascending=False),
        x="distancia_total_km",
        y="type",
        orientation='h',
        title="Distância Total por Tipo de Atividade",
        color="type",
        labels={"distancia_total_km": "Distância Total (km)", "type": "Tipo de Atividade"},
        text='distancia_total_km'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_comparativo, use_container_width=True, hide_index=True)


def exibir_comparativo_individual(df):
    """
    Mostra os seletores e as métricas para comparar duas atividades.
    """
    st.header("Comparar Duas Atividades Específicas 🥊")
    st.write("Selecione duas atividades da lista (baseada nos seus filtros) para um 'head-to-head'.")
    
    lista_atividades = df.sort_values(by='data_inicio', ascending=False)['display_name'].tolist()
    
    col_a, col_b = st.columns(2)
    
    atividade_1_nome = col_a.selectbox("Selecione a Atividade 1:", lista_atividades, index=0, key="comp_ativ_1")
    atividade_2_nome = col_b.selectbox("Selecione a Atividade 2:", lista_atividades, index=1 if len(lista_atividades) > 1 else 0, key="comp_ativ_2")
    
    # Pega os dados completos das atividades selecionadas
    dados_1 = df[df['display_name'] == atividade_1_nome].iloc[0]
    dados_2 = df[df['display_name'] == atividade_2_nome].iloc[0]
    
    # Cria colunas para mostrar os resultados lado a lado
    col_metrica1, col_metrica2 = st.columns(2)
    
    # Nomes das atividades
    col_metrica1.markdown(f"**{dados_1['name']}**")
    col_metrica2.markdown(f"**{dados_2['name']}**")
    
    col_metrica1.metric("Distância (km)", f"{dados_1['distancia_km']:.2f}")
    col_metrica2.metric("Distância (km)", f"{dados_2['distancia_km']:.2f}")

    col_metrica1.metric("Pace Médio", f"{dados_1['pace_formatado']}")
    col_metrica2.metric("Pace Médio", f"{dados_2['pace_formatado']}")

    col_metrica1.metric("Tempo (horas)", f"{dados_1['tempo_horas']:.2f}")
    col_metrica2.metric("Tempo (horas)", f"{dados_2['tempo_horas']:.2f}")

    col_metrica1.metric("Elevação (m)", f"{dados_1['total_elevation_gain']:.2f}")
    col_metrica2.metric("Elevação (m)", f"{dados_2['total_elevation_gain']:.2f}")
    
    # --- MELHORIAS NO COMPARE (com .get() para segurança) ---
    vel_max_1 = (dados_1.get('max_speed', 0) * 3.6).round(2)
    vel_max_2 = (dados_2.get('max_speed', 0) * 3.6).round(2)
    col_metrica1.metric("Velocidade Máx (km/h)", f"{vel_max_1}")
    col_metrica2.metric("Velocidade Máx (km/h)", f"{vel_max_2}")
    
    fc_1 = dados_1.get('average_heartrate', 'N/A')
    fc_2 = dados_2.get('average_heartrate', 'N/A')
    col_metrica1.metric("FC Média ❤️", f"{fc_1}")
    col_metrica2.metric("FC Média ❤️", f"{fc_2}")
    
    watts_1 = dados_1.get('average_watts', 'N/A')
    watts_2 = dados_2.get('average_watts', 'N/A')
    col_metrica1.metric("Potência Média (W) ⚡", f"{watts_1}")
    col_metrica2.metric("Potência Média (W) ⚡", f"{watts_2}")

    col_metrica1.metric("Kudos 👍", f"{dados_1['kudos_count']}")
    col_metrica2.metric("Kudos 👍", f"{dados_2['kudos_count']}")


def exibir_detalhes_atividade(df_filtrado, headers):
    """
    Cria a seção de análise profunda para uma atividade selecionada.
    """
    st.write("---")
    st.header("Análise Profunda por Atividade 🔬")
    
    # 1. Seletor de Atividade
    lista_atividades = df_filtrado.sort_values(by='data_inicio', ascending=False)['display_name'].tolist()
    atividade_selecionada_nome = st.selectbox(
        "Selecione uma atividade para análise detalhada:",
        lista_atividades,
        index=0,
        key="detalhe_atividade_select"
    )
    
    # 2. Obter o ID da atividade selecionada
    # Usamos .loc para pegar a linha inteira e depois o 'id'
    activity_id = df_filtrado.loc[df_filtrado['display_name'] == atividade_selecionada_nome, 'id'].iloc[0]

    # 3. Chamar a API de Detalhes
    with st.spinner(f"Buscando detalhes da atividade '{atividade_selecionada_nome}'..."):
        detalhes, erro = carregar_detalhes_atividade(activity_id, headers)

    if erro:
        st.error(f"Não foi possível carregar os detalhes: {erro}")
        return
    
    # 4. Exibir Resumo e Mapa
    st.subheader(f"Resumo: {detalhes.get('name', 'Atividade')}")
    
    mapa_col, resumo_col = st.columns([1, 1]) # Duas colunas
    
    with mapa_col:
        # Decodifica e exibe o mapa
        polyline_str = detalhes.get('map', {}).get('polyline', '')
        map_data = decodificar_mapa(polyline_str)
        if map_data is not None:
            
            # --- CÓDIGO NOVO (COM PLOTLY) ---
            
            # 1. Cria a figura do mapa com uma linha
            fig_mapa = px.line_mapbox(
                map_data,
                lat="lat",
                lon="lon",
                zoom=12,  # Zoom inicial (ajuste conforme necessário)
                height=500
            )
            
            # 2. Configura o layout do mapa
            fig_mapa.update_layout(
                mapbox_style="open-street-map", # Estilo do mapa
                margin={"r":0,"t":0,"l":0,"b":0} # Remove margens brancas
            )
            
            # 3. Define a cor (Laranja Strava) e a espessura da linha (fina)
            fig_mapa.update_traces(line=dict(color="#FF4B00", width=3))
            
            # 4. Exibe o gráfico do Plotly no Streamlit
            st.plotly_chart(fig_mapa, use_container_width=True)

        else:
            st.info("Nenhum mapa disponível para esta atividade.")
            
    with resumo_col:
        # KPIs da atividade selecionada
        st.metric("Distância", f"{(detalhes.get('distance', 0) / 1000):.2f} km")
        st.metric("Tempo", f"{(detalhes.get('moving_time', 0) / 3600):.2f} h")
        st.metric("Elevação", f"{detalhes.get('total_elevation_gain', 0)} m")
        st.metric("Calorias", f"{detalhes.get('calories', 0):.0f} kcal")
        
        # Pega o pace (se existir nos dados tratados)
        pace = df_filtrado.loc[df_filtrado['id'] == activity_id, 'pace_formatado'].iloc[0]
        st.metric("Pace Médio", pace)

    # 5. Exibir Splits (Gráfico de Barras Horizontal)
    st.subheader("Pace por Quilômetro (Splits)")
    if 'splits_metric' in detalhes and detalhes['splits_metric']:
        df_splits = pd.DataFrame(detalhes['splits_metric'])
        
        # Calcula o pace em minutos decimais
        df_splits['pace_min_decimal'] = df_splits['moving_time'] / 60
        
        # Formata o pace para exibição (ex: "5:30")
        def formatar_pace_split(segundos):
            minutos = int(segundos // 60)
            segundos_rest = int(segundos % 60)
            return f"{minutos:02}:{segundos_rest:02}"
            
        df_splits['pace_formatado'] = df_splits['moving_time'].apply(formatar_pace_split)
        
        # Cria a coluna 'km' como string para o gráfico
        df_splits['km'] = (df_splits['split']).astype(str)
        
        # Cria o gráfico de barras horizontal com Plotly
        fig_splits = px.bar(
            df_splits,
            x='pace_min_decimal',
            y='km',
            orientation='h',
            title="Pace por KM (min/km)",
            text='pace_formatado' # Mostra o texto formatado na barra
        )
        # Inverte o eixo Y para que o KM 1 fique no topo
        fig_splits.update_layout(
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Pace (Minutos por KM)",
            plot_bgcolor='rgba(0,0,0,0)', # Fundo transparente
            paper_bgcolor='rgba(0,0,0,0)' # Fundo transparente
        )
        st.plotly_chart(fig_splits, use_container_width=True)
    else:
        st.info("Nenhum split métrico (km) encontrado para esta atividade.")

    # 6. Exibir Segmentos
    st.subheader("Desempenho nos Segmentos")
    if 'segment_efforts' in detalhes and detalhes['segment_efforts']:
        df_segmentos = pd.DataFrame(detalhes['segment_efforts'])
        cols_segmentos = ['name', 'distance', 'elapsed_time', 'pr_rank', 'kom_rank']
        
        # Filtra colunas que realmente existem
        cols_existentes = [col for col in cols_segmentos if col in df_segmentos.columns]
        
        st.dataframe(df_segmentos[cols_existentes], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum segmento encontrado para esta atividade.")


def exibir_tabela_dados(df):
    """
    Mostra a tabela de dados filtrados no final.
    """
    st.write("---")
    st.header("Tabela de Dados Filtrados")
    
    colunas_uteis = [
        'name', 'data_inicio', 'type', 'distancia_km', 'tempo_horas', 
        'vel_media_kmh', 'pace_formatado', 'total_elevation_gain', 
        'kudos_count', 'average_heartrate', 'average_watts'
    ]
    # Filtra colunas que realmente existem no DataFrame
    colunas_existentes = [col for col in colunas_uteis if col in df.columns]
    
    st.data_editor(
        df[colunas_existentes].sort_values(by='data_inicio', ascending=False),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )

# --- 5. CORPO PRINCIPAL DO APP (LÓGICA DE EXECUÇÃO) ---

# Carrega os dados do atleta e o clima PRIMEIRO
dados_atleta, erro_atleta = carregar_dados_atleta(f"{URL_BASE}/athlete", HEADERS)
clima = "Indisponível" # Valor padrão

if erro_atleta:
    st.error(erro_atleta)
    st.stop()
else:
    clima = carregar_clima(dados_atleta.get('city'))
    # NÃO exibimos o cabeçalho aqui ainda, pois precisamos dos dados FILTRADOS


# Carrega o restante dos dados (atividades)
with st.spinner("Buscando seu histórico de atividades... Isso pode levar um minuto se for a primeira vez."):
    df_bruto, erro_atividades = carregar_todas_atividades(f"{URL_BASE}/athlete/activities", HEADERS)

# Agora, checamos o resultado FORA da função cacheada
if erro_atividades:
    st.error(erro_atividades) # Mostra o erro que a função retornou
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
    
    # 2. Mostra os filtros e obtém o dataframe filtrado
    df_filtrado = exibir_sidebar_filtros(df_tratado)
    
    # 3. AGORA SIM: Exibe o cabeçalho com os dados do atleta, clima E os KPIs filtrados
    exibir_cabecalho(dados_atleta, clima, df_filtrado)
    
    if df_filtrado.empty:
        st.warning("Nenhuma atividade encontrada com os filtros selecionados.")
    else:
        # Exibe todos os módulos do dashboard
        
        st.write("---")
        exibir_comparativo_tipos(df_filtrado)
        
        st.write("---")
        exibir_comparativo_individual(df_filtrado)
        
        # --- EXIBE A NOVA SEÇÃO DE DETALHES ---
        exibir_detalhes_atividade(df_filtrado, HEADERS)
        
        exibir_tabela_dados(df_filtrado)
except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}")
    st.exception(e) # Mostra o traceback completo para debug