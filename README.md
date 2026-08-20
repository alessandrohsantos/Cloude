# Controle de Faturas de Cartão de Crédito

Aplicação fullstack para consolidar faturas do **Nubank**, **Itaú** e **Santander** diretamente do Gmail, com categorização automática de gastos e previsão de tendências futuras. Também inclui um módulo de **consumo de água** que importa as leituras diárias do portal Vedrano do condomínio e calcula o valor estimado da conta.

## Funcionalidades

- **Leitura de faturas via Gmail** — busca emails dos 3 bancos no período configurado
- **Categorização automática** — classifica transações em 13 categorias usando regras por palavras-chave
- **Dashboard interativo** — gráficos de pizza, barras e linhas de tendência
- **Previsão de gastos** — regressão linear projeta os próximos 3 meses por categoria
- **Filtros e busca** — filtre por banco, categoria e descrição
- **Edição de categorias** — corrija classificações diretamente na tabela
- **Consumo de água (Vedrano)** — importa as leituras diárias do portal do condomínio e calcula o valor da conta por faixa tarifária progressiva

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

# Água (Vedrano)
VEDRANO_LOGIN=xxxx
VEDRANO_SENHA=xxxx
VEDRANO_LOGIN_URL=https://consultaleituras.vedrano.com.br/login-externo
VEDRANO_DEBUG=0
```

---

## Módulo de Água (Vedrano)

Importa as leituras diárias de consumo de água do portal do condomínio
(consultaleituras.vedrano.com.br) via automação de navegador e calcula o valor
estimado da conta por faixa tarifária progressiva.

### Configuração

1. **Credenciais do portal**: preencha `VEDRANO_LOGIN` e `VEDRANO_SENHA` no
   `.env` do backend — são os dados recebidos por e-mail da administradora
   ("Login Água" / "Senha Água").
2. **Navegador do Playwright** (só na primeira vez):
   ```bash
   cd backend
   playwright install chromium
   ```
3. **Tarifa**: edite `backend/app/water/sabesp_tarifas.json` com os valores de
   R$/m³ atuais (água e esgoto) por faixa de consumo — pegue no site da Sabesp
   ou na sua própria conta de água — e mude `"configurado"` para `true`.
   Enquanto isso não for feito, o dashboard mostra o consumo normalmente mas
   o valor calculado fica zerado, com um aviso.

### Uso

Na aba **💧 Água** do app, clique em "Sincronizar com o Vedrano" para importar
as leituras mais recentes. O dashboard mostra o consumo diário, o consumo do
mês, o detalhamento por faixa tarifária e o valor total estimado da conta
(água + esgoto + taxa fixa, se configurada).

### Se a sincronização falhar

O portal Vedrano não tem API pública, então a importação usa automação de
navegador com seletores heurísticos que não puderam ser validados contra o
site real durante o desenvolvimento. Se o login ou a extração das leituras
falhar:

```bash
# no .env do backend
VEDRANO_DEBUG=1
```

Isso salva screenshot, HTML e as respostas JSON capturadas da página em
`backend/debug_vedrano/` (pasta ignorada pelo git) para diagnosticar e
ajustar os seletores em `backend/app/water/vedrano_client.py`.

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
│   ├── parsers/
│   │   ├── base.py      # Utilitários (parse valor BR, data PT)
│   │   ├── nubank.py    # Parser emails Nubank
│   │   ├── itau.py      # Parser emails + PDF Itaú
│   │   └── santander.py # Parser emails + PDF Santander
│   └── water/
│       ├── vedrano_client.py  # Login + scraping do portal Vedrano (Playwright)
│       ├── tariff.py          # Cálculo da conta por faixa tarifária progressiva
│       ├── analytics.py       # Agregação das leituras (diário/mensal)
│       └── sabesp_tarifas.json # Tabela de tarifas editável (água/esgoto por faixa)

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
        ├── TransactionTable.tsx # Tabela com filtros e edição
        └── water/
            ├── WaterDashboard.tsx        # Container + botão de sincronização
            ├── WaterSummaryCards.tsx     # Cards de resumo (consumo, valor, etc.)
            ├── WaterConsumptionChart.tsx # Gráfico de consumo diário
            └── WaterBillBreakdown.tsx    # Detalhamento por faixa tarifária
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
