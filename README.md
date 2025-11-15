# 🏃‍♂️ Dashboard de Análise de Atividades do Strava

![Streamlit](https://img.shields.io/badge/Streamlit-1.46.1-FF4B4B?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.3.0-150458?style=for-the-badge&logo=pandas)
![Plotly](https://img.shields.io/badge/Plotly-6.3.0-3F4F75?style=for-the-badge&logo=plotly)

Um dashboard interativo construído com Streamlit para visualizar e analisar seus dados de atividades do Strava.

## 🌟 Visão Geral

Este projeto permite que você conecte sua conta Strava de forma segura via OAuth2 e explore seu histórico de atividades através de gráficos e tabelas interativas. A aplicação oferece uma visão geral do seu desempenho, permite comparar atividades, analisar o ritmo de corridas específicas e muito mais.

*(Aqui você pode adicionar um GIF ou uma screenshot do dashboard em ação)*
`![Dashboard Screenshot](URL_DA_IMAGEM_AQUI)`

---

## ✨ Funcionalidades Principais

- **Autenticação Segura:** Login com sua conta Strava usando o protocolo OAuth2.
- **Dashboard Geral:** KPIs (Indicadores Chave de Performance) com seus totais de distância, tempo, elevação e número de atividades.
- **Filtros Dinâmicos:** Filtre suas atividades por ano, tipo (corrida, ciclismo, etc.), período, categoria da corrida e até mesmo pelo tênis utilizado.
- **Análise Comparativa:**
    - **Visão Geral por Tipo:** Compare o total e a média de distância, tempo e pace entre diferentes tipos de esporte.
    - **Comparação Individual:** Selecione duas atividades quaisquer e compare suas métricas lado a lado.
- **Análise Profunda de Atividade:**
    - Visualize o trajeto da atividade em um mapa interativo.
    - Analise o ritmo (pace) de cada quilômetro em gráficos de barra e de linha.
    - Veja detalhes de todos os segmentos percorridos.
- **Visualização de Dados:** Gráficos interativos para análise de evolução, desempenho e correlações entre métricas.
- **Tabela de Dados:** Todos os dados filtrados são exibidos em uma tabela que pode ser ordenada e explorada.

---

## 🛠️ Tecnologias Utilizadas

- **Backend & Frontend:** [Streamlit](https://streamlit.io/)
- **Análise de Dados:** [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/)
- **Visualização de Dados:** [Plotly](https://plotly.com/python/)
- **Comunicação com a API:** [Requests](https://requests.readthedocs.io/en/latest/)
- **Decodificação de Rotas:** [Polyline](https://pypi.org/project/polyline/)

---

## 🚀 Como Instalar e Executar o Projeto

Siga os passos abaixo para configurar e executar o projeto em sua máquina local.

### 1. Pré-requisitos

- [Python 3.9+](https://www.python.org/downloads/)
- Uma conta no [Strava](https://www.strava.com/)

### 2. Crie sua Aplicação no Strava

Para usar a API do Strava, você precisa registrar uma aplicação:
1.  Acesse a página [Strava API Settings](https://www.strava.com/settings/api).
2.  Clique em **"Criar e Gerenciar seu Aplicativo"** (ou similar).
3.  Preencha o formulário:
    - **Nome do Aplicativo:** Dê um nome, por exemplo, "Meu Dashboard".
    - **Site:** Pode ser `http://localhost`.
    - **Domínio de Autorização:** Coloque `localhost`.
    - **Logo:** Opcional.
4.  Após criar, você receberá seu **ID de Cliente** (Client ID) e **Segredo do Cliente** (Client Secret). Guarde esses valores!

### 3. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

### 4. Instale as Dependências

As dependências do projeto estão listadas no arquivo `requirements.txt`. Para instalá-las, execute:

```bash
pip install -r requirements.txt
```

### 5. Configure suas Credenciais

Crie o arquivo de segredos para armazenar suas credenciais do Strava de forma segura:
1.  Na raiz do projeto, crie uma pasta chamada `.streamlit`.
2.  Dentro dela, crie um arquivo chamado `secrets.toml`.
3.  Adicione o seguinte conteúdo ao arquivo, substituindo pelos valores que você obteve no passo 2:

```toml
# .streamlit/secrets.toml

CLIENT_ID = "SEU_CLIENT_ID_AQUI"
CLIENT_SECRET = "SEU_CLIENT_SECRET_AQUI"
```

### 6. Execute a Aplicação

Com tudo configurado, inicie a aplicação Streamlit com o seguinte comando:

```bash
streamlit run login.py
```

Seu navegador abrirá automaticamente no endereço `http://localhost:8501`. Na primeira vez, você será redirecionado para a página de autorização do Strava. Autorize o aplicativo e comece a explorar seus dados!

---

## 📂 Estrutura do Projeto

```
.
├── .streamlit/
│   └── secrets.toml    # Arquivo para credenciais da API (NÃO versionar)
├── .gitignore          # Arquivos e pastas a serem ignorados pelo Git
├── app_strava.py       # Lógica principal do dashboard
├── correlacao.py       # Módulo para a aba de correlação
├── desempenho_corridas.py # Módulo para a aba de desempenho
├── evolucao_provas.py  # Módulo para a aba de evolução em provas
├── evolucao_tempo.py   # Módulo para a aba de evolução no tempo
├── login.py            # Ponto de entrada da aplicação, gerencia o login
├── README.md           # Este arquivo
└── requirements.txt    # Dependências do projeto
```
