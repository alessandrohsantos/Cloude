# Controle de Faturas de Cartão de Crédito

Aplicação fullstack para consolidar faturas do **Nubank**, **Itaú** e **Santander** diretamente do Gmail, com categorização automática de gastos e previsão de tendências futuras.

## Funcionalidades

- **Leitura de faturas via Gmail** — busca emails dos 3 bancos no período configurado
- **Categorização automática** — classifica transações em 13 categorias usando regras por palavras-chave
- **Dashboard interativo** — gráficos de pizza, barras e linhas de tendência
- **Previsão de gastos** — regressão linear projeta os próximos 3 meses por categoria
- **Filtros e busca** — filtre por banco, categoria e descrição
- **Edição de categorias** — corrija classificações diretamente na tabela

## Pré-requisitos

- Python 3.10+
- Node.js 18+
- Conta Google com Gmail
- Google Cloud Project com Gmail API habilitada

---

## Configuração do Google Cloud

### 1. Criar projeto e habilitar Gmail API

```bash
# Acesse: https://console.cloud.google.com
# Crie um novo projeto: "credit-card-tracker"

# Habilite a Gmail API:
# APIs & Services > Enable APIs > Gmail API > Enable
```

### 2. Configurar OAuth 2.0

```
APIs & Services > Credentials > Create Credentials > OAuth client ID
  Application type: Web application
  Name: Credit Card Tracker
  Authorized redirect URIs: http://localhost:8000/auth/callback
```

Copie o **Client ID** e **Client Secret** gerados.

### 3. Configurar tela de consentimento

```
APIs & Services > OAuth consent screen
  User Type: External
  App name: Controle de Faturas
  Scopes: gmail.readonly, email, openid
  Test users: seu email
```

---

## Instalação e Execução

### Backend

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais do Google Cloud

# Rodar
python run.py
# API disponível em http://localhost:8000
# Docs em http://localhost:8000/docs
```

### Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev
# App disponível em http://localhost:5173
```

---

## Configuração do .env

```env
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=gere-uma-chave-secreta-aqui
DATABASE_URL=sqlite:///./creditcards.db
FRONTEND_URL=http://localhost:5173
```

---

## Arquitetura

```
backend/
├── app/
│   ├── main.py          # FastAPI: endpoints REST
│   ├── auth.py          # Google OAuth2 flow
│   ├── gmail.py         # Gmail API client + busca
│   ├── database.py      # SQLite via SQLAlchemy
│   ├── models.py        # Modelos Pydantic + SQLAlchemy
│   ├── categorizer.py   # Classificação por palavras-chave
│   ├── analytics.py     # Agregações + regressão linear
│   └── parsers/
│       ├── base.py      # Utilitários (parse valor BR, data PT)
│       ├── nubank.py    # Parser emails Nubank
│       ├── itau.py      # Parser emails + PDF Itaú
│       └── santander.py # Parser emails + PDF Santander

frontend/
└── src/
    ├── App.tsx               # App principal + roteamento
    ├── api/client.ts         # Axios para o backend
    ├── utils.ts              # Formatação + constantes
    └── components/
        ├── SummaryCards.tsx  # Cards de resumo (total, média, previsão)
        ├── CategoryChart.tsx # Pizza + barras por categoria
        ├── TrendChart.tsx    # Linha temporal + forecast
        ├── MonthlyChart.tsx  # Barras empilhadas por banco
        └── TransactionTable.tsx # Tabela com filtros e edição
```

## Como funciona a previsão de tendências

1. **Coleta histórica**: busca transações dos N meses selecionados
2. **Agrupamento mensal**: soma por mês e por categoria
3. **Regressão linear**: ajusta uma reta aos dados históricos (numpy polyfit)
4. **Projeção**: extrapola os próximos 3 meses com a tendência calculada
5. **Por categoria**: mesma lógica aplicada individualmente a cada categoria

A linha laranja no gráfico de tendências mostra a reta de regressão. Se os gastos estão crescendo mês a mês, a previsão refletirá isso.

## Bancos suportados

| Banco | Tipo de email | PDF |
|-------|--------------|-----|
| Nubank | Notificações de transação + fatura mensal | Não |
| Itaú | Fatura mensal + HTML resumo | Sim |
| Santander | Fatura mensal | Sim |

Os parsers usam múltiplos padrões regex e BeautifulSoup para máxima cobertura dos formatos de email que cada banco envia.
