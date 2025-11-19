import secrets as py_secrets
import time
from typing import Optional

import requests
import streamlit as st

from app_strava import show_main_dashboard


DEFAULT_CLIENT_ID = st.secrets.get("CLIENT_ID", "")
DEFAULT_CLIENT_SECRET = st.secrets.get("CLIENT_SECRET", "")
DEFAULT_REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501")


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str):
    """Troca o código de autorização por um token de acesso."""
    try:
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error("Falha na comunicação com a API do Strava ao trocar o código pelo token.")
        print(f"[Strava OAuth] Erro ao trocar token: {e}")
        return None


def refresh_token_if_needed():
    """Renova o token se estiver próximo do vencimento."""
    token_data = st.session_state.get("strava_token_data")
    client_config = st.session_state.get("client_config")
    if not token_data or not client_config:
        return

    expires_at = token_data.get("expires_at", 0)
    if expires_at and expires_at > time.time() + 60:
        return  # Ainda válido

    try:
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": token_data.get("refresh_token"),
            },
            timeout=15,
        )
        response.raise_for_status()
        refreshed = response.json()
        st.session_state["strava_token_data"] = refreshed
    except requests.exceptions.RequestException as e:
        st.error("Token expirado e não foi possível renovar. Faça login novamente.")
        print(f"[Strava OAuth] Erro ao renovar token: {e}")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def show_login_page():
    """Exibe a página de login e gerencia a lógica de autenticação em duas etapas."""
    st.title("Login Strava")

    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = py_secrets.token_urlsafe(16)

    query_params = dict(st.query_params)

    has_secret = bool(DEFAULT_CLIENT_SECRET)

    # Etapa 2: retorna do Strava com o código
    if "code" in query_params:
        code = query_params.get("code")
        client_id = query_params.get("client_id") or st.session_state.get("client_id_pending") or DEFAULT_CLIENT_ID
        state = query_params.get("state")

        expected_state = st.session_state.get("oauth_state")
        if expected_state and state and state != expected_state:
            st.warning("State diferente do esperado. Se reabriu em outra aba, continue se reconhecer esta sessão.")

        st.subheader("Etapa 2 de 2: Confirme suas credenciais")
        st.success(f"Autorização recebida para o Client ID: `{client_id}`")

        if has_secret:
            client_secret = DEFAULT_CLIENT_SECRET
            st.caption("Client Secret carregado automaticamente do servidor (você não precisa preencher nada).")
            do_login = st.button("Concluir login")
        else:
            st.info("Para completar o login, insira o Client Secret (somente quem configurou o app).")
            client_secret = st.text_input("Client Secret", type="password", value=DEFAULT_CLIENT_SECRET, key="client_secret_input")
            do_login = st.button("Login")

        if do_login:
            if not client_secret:
                st.warning("Por favor, insira o Client Secret.")
            else:
                with st.spinner("Finalizando autenticação..."):
                    token_data = exchange_code_for_token(client_id, client_secret, code, DEFAULT_REDIRECT_URI)

                if token_data:
                    st.session_state["strava_token_data"] = token_data
                    st.session_state["logged_in"] = True
                    st.session_state["client_config"] = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": DEFAULT_REDIRECT_URI,
                    }
                    st.session_state.pop("auth_url", None)
                    st.session_state.pop("client_id_pending", None)
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("A troca do token falhou. Verifique o Client Secret e tente novamente.")

    # Etapa 1: inserção dos dados e redirecionamento ao Strava
    else:
        st.subheader("Etapa 1 de 2: Autorize o acesso")
        client_id_input = st.text_input(
            "Client ID",
            value=DEFAULT_CLIENT_ID,
            key="client_id_input",
            disabled=bool(DEFAULT_CLIENT_ID),
            help="Preencha apenas se o campo não estiver carregado automaticamente.",
        )

        if st.button("Gerar link de autorização"):
            if client_id_input:
                state = st.session_state["oauth_state"]
                redirect_uri_with_client = f"{DEFAULT_REDIRECT_URI}?client_id={client_id_input}"
                auth_url = (
                    "https://www.strava.com/oauth/authorize?"
                    f"client_id={client_id_input}&redirect_uri={redirect_uri_with_client}"
                    "&response_type=code&scope=read_all,profile:read_all,activity:read_all"
                    f"&state={state}"
                )
                st.session_state["auth_url"] = auth_url
                st.session_state["client_id_pending"] = client_id_input
            else:
                st.warning("Por favor, insira o Client ID.")

        if st.session_state.get("auth_url"):
            st.link_button("Ir para autorização no Strava", st.session_state["auth_url"], type="primary")
            st.caption("Se o botão não abrir, copie e cole o link abaixo no navegador:")
            st.code(st.session_state["auth_url"], language="text")

    with st.expander("Como obter as credenciais da API do Strava?"):
        st.markdown(
            """
            Se você está apenas usando o app publicado:
            - Basta clicar em "Gerar link de autorização" e autorizar no Strava. O Client Secret já está salvo no servidor.

            Se você vai hospedar o app:
            1. Acesse [Strava API Settings](http://www.strava.com/settings/api) com sua conta Strava.
            2. Clique em “Create & Manage Your App” e crie uma aplicação.
               - Application Name: escolha um nome (ex.: "Dashboard Pace de 6").
               - Website: pode ser `http://localhost`.
               - Authorization Callback Domain: use `localhost` (ou o domínio onde vai rodar).
            3. Após salvar, copie **Client ID** e **Client Secret** exibidos na página.
            4. No servidor/local, crie a pasta `.streamlit` (se não existir) e dentro dela o arquivo `secrets.toml` com:
               ```
               CLIENT_ID = "SEU_CLIENT_ID"
               CLIENT_SECRET = "SEU_CLIENT_SECRET"
               REDIRECT_URI = "http://localhost:8501"
               ```
               Ajuste o `REDIRECT_URI` se estiver usando outro domínio/porta e o mesmo valor no painel do Strava.
            """
        )


# -------------------------------------------------------------------
# Lógica principal
# -------------------------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state.get("logged_in"):
    refresh_token_if_needed()
    access_token = st.session_state["strava_token_data"]["access_token"]
    show_main_dashboard(access_token)
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
else:
    show_login_page()
