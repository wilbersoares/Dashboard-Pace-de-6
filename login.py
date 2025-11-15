import streamlit as st
import requests
from datetime import datetime
from app_strava import show_main_dashboard

# --- Funções Auxiliares ---

def exchange_code_for_token(client_id, client_secret, code):
    """Troca o código de autorização por um token de acesso."""
    try:
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Falha na comunicação com a API do Strava: {e}")
        if e.response is not None:
            st.error(f"Detalhes da resposta: {e.response.text}")
        return None

def show_login_page():
    """Exibe a página de login e gerencia a lógica de autenticação em duas etapas."""
    st.title("Login Strava")
    query_params = st.query_params

    # --- Etapa 2: Confirmação e Troca de Token (após retornar do Strava) ---
    if "code" in query_params and "client_id" in query_params:
        code = query_params.get("code")
        client_id = query_params.get("client_id")

        st.subheader("Etapa 2 de 2: Confirme suas Credenciais")
        st.success(f"Autorização recebida para o Client ID: `{client_id}`")
        st.info("Para completar o login, por favor, insira seu Client Secret.")

        client_secret = st.text_input("Client Secret", type="password")

        if st.button("Login"):
            if not client_secret:
                st.warning("Por favor, insira o Client Secret.")
            else:
                with st.spinner("Finalizando autenticação..."):
                    token_data = exchange_code_for_token(client_id, client_secret, code)
                
                if token_data:
                    st.session_state['strava_token_data'] = token_data
                    st.session_state['logged_in'] = True
                    # Limpa a URL para a próxima execução
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("A troca do token falhou. Verifique se o Client Secret está correto e tente novamente.")

    # --- Etapa 1: Inserir Client ID e redirecionar ---
    else:
        st.subheader("Etapa 1 de 2: Insira seu Client ID")
        client_id_input = st.text_input("Client ID")

        if st.button("Autorizar no Strava"):
            if client_id_input:
                # Passa o client_id na URL de redirecionamento
                redirect_uri = f"http://localhost:8501?client_id={client_id_input}"
                auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id_input}&redirect_uri={redirect_uri}&response_type=code&scope=read_all,profile:read_all,activity:read_all"
                
                # Redireciona o usuário
                st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                st.spinner("Redirecionando para o Strava...")
            else:
                st.warning("Por favor, insira seu Client ID.")

    # Expander com as instruções
    with st.expander("Como obter as credenciais da API do Strava?"):
        st.markdown(
            """
            1. Acesse [Strava API Settings](http://www.strava.com/settings/api).
            2. Crie uma nova aplicação.
            3. Em "Authorization Callback Domain", coloque `localhost`.
            4. Copie o "Client ID" e o "Client Secret".
            """
        )

# --- Lógica Principal ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state.get('logged_in'):
    access_token = st.session_state['strava_token_data']['access_token']
    show_main_dashboard(access_token)
    if st.sidebar.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
else:
    show_login_page()
