<<<<<<< HEAD
# Dashboard de Análise de Atividades do Strava
=======
# 🏃‍♂️ Dashboard PACE de 6 para Análise de Atividades do Strava
>>>>>>> bfbf1c1fbb1c7621d782c4202739fdd9fc881a60

Dashboard em Streamlit para explorar dados do Strava com KPIs, gráficos interativos e análises focadas em corridas.

## Como usar (quem está acessando o app publicado)
- Clique em “Gerar link de autorização”, autorize no Strava e conclua o login.
- Você NÃO precisa editar arquivos nem saber o Client Secret; ele já fica salvo no servidor.

## Como hospedar você mesmo (passo a passo)
1) Criar app no Strava  
   - Entre em: https://www.strava.com/settings/api (faça login).  
   - Clique em “Create & Manage Your App” → “Create”.  
   - Preencha:  
     - **Application Name**: ex. “Dashboard Pace de 6”.  
     - **Website**: `http://localhost` (ou seu domínio).  
     - **Authorization Callback Domain**: `localhost` (ou seu domínio).  
   - Salve e anote **Client ID** e **Client Secret**.

2) Guardar o segredo com segurança  
   - Na raiz do projeto, crie a pasta `.streamlit` (se não existir).  
   - Dentro dela, crie `secrets.toml` e coloque (mantenha as aspas):
```toml
CLIENT_ID = "SEU_CLIENT_ID"
CLIENT_SECRET = "SEU_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8501"
```
   - Se for usar outro domínio/porta, ajuste o `REDIRECT_URI` e o mesmo valor no painel do Strava.

3) Instalar dependências  
```bash
pip install -r requirements.txt
```

4) Rodar  
```bash
python -m streamlit run login.py
```

## Estrutura
- `login.py` – fluxo de login (usa Client Secret do servidor quando disponível).  
- `app_strava.py` – layout principal, filtros e navegação em abas.  
- `evolucao_tempo.py`, `desempenho_corridas.py`, `evolucao_provas.py`, `correlacao.py` – análises específicas.
