# 🛒 Automação de Compras — Pipeline End-to-End

> Projeto de portfólio demonstrando habilidades de **Analista + Engenheiro de Dados**:  
> pipeline ETL automatizado, banco PostgreSQL com 1M+ registros, dashboard Power BI  
> e sistema de alertas inteligentes — simulando um ambiente corporativo real com ERP.

---

## 🏗️ Arquitetura do Projeto

```
simulador.py          →  Simula 20 compradores gerando pedidos (como SAP/TOTVS)
     ↓
database.py           →  ETL: carrega dados no PostgreSQL (tabelas, views, índices)
     ↓
analise.py            →  KPIs + 4 gráficos + relatório Excel com 6 abas
     ↓
alertas.py            →  Detecta estoque crítico, gastos anômalos, concentração de fornecedor
     ↓
email_service.py      →  Relatório semanal automático via Outlook
     ↓
scheduler.py          →  Orquestra tudo: pipeline diário às 08h, email toda segunda
     ↓
Power BI              →  Dashboard conectado ao PostgreSQL — atualiza automaticamente
```

---

## 📊 KPIs do Dataset

| KPI | Valor |
|-----|-------|
| 💰 Total Gasto | R$ 31,07 bilhões |
| 📋 Total de Pedidos | 1.000.000 |
| 🎯 Ticket Médio | R$ 31.072,30 |
| 🏭 Fornecedores Ativos | 734 |
| 📦 Categorias | 7 |
| 📅 Período | 2018 → 2024 |
| ⚠️ Estoque Crítico | 585 produtos |

---

## 🚀 Como Rodar

### 1. Pré-requisitos

- Python 3.10+
- PostgreSQL 14+ rodando localmente
- Power BI Desktop + driver [Npgsql 4.0.x](https://github.com/npgsql/npgsql/releases/download/v4.0.13/Npgsql-4.0.13.msi)

### 2. Instalação

```bash
git clone https://github.com/DataKleber/automacao-compras.git
cd automacao-compras

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuração

Crie o arquivo `.env` na raiz:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=automacao-compras
DB_USER=postgres
DB_PASSWORD=postgres123
```

Coloque os arquivos de dados em `dados/`:
```
dados/
├── compras_1M.xlsx
├── estoque_10k.xlsx
└── fornecedores_1k.xlsx
```

### 4. Executar

```bash
# Carga inicial (1M de registros → ~10 minutos)
python database.py

# Pipeline completo (análise + relatório)
python main.py

# Simular um dia de compras (20 compradores)
python simulador.py

# Verificar alertas
python alertas.py

# Iniciar scheduler (roda todo dia às 8h)
python scheduler.py

# Rodar pipeline agora (testes)
python scheduler.py --agora
```

---

## 📁 Estrutura de Arquivos

```
automacao-compras/
│
├── simulador.py         ← Simula ERP (20 compradores, perfis por categoria)
├── database.py          ← Carga PostgreSQL: tabelas, índices, views
├── analise.py           ← KPIs, 4 gráficos, relatório Excel 6 abas
├── alertas.py           ← Alertas: estoque, gastos, anomalias, concentração
├── email_service.py     ← Relatório semanal automático via Outlook
├── scheduler.py         ← Orquestra pipeline diário + email semanal
├── main.py              ← Ponto de entrada: python main.py
├── requirements.txt
├── .gitignore
│
├── dados/               ← xlsx de entrada (não versionados)
└── relatorios/          ← relatórios e gráficos gerados (não versionados)
```

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10 |
| Banco de Dados | PostgreSQL 16 |
| ETL / ORM | SQLAlchemy, psycopg2 |
| Análise | Pandas |
| Visualização | Matplotlib, Seaborn |
| Relatório | OpenPyXL, XlsxWriter |
| Dashboard | Power BI Desktop |
| Agendamento | Schedule |
| Automação Email | PyWin32 (Outlook) |
| Versionamento | Git / GitHub |

---

## 🧠 Conceitos Demonstrados

**Engenharia de Dados**
- Modelagem relacional com chaves estrangeiras, índices e views materializadas
- ETL em batch com controle de chunks (50k linhas)
- Pipeline orquestrado com agendamento automático
- Simulação de integração com ERP corporativo (SAP/TOTVS)

**Análise de Dados**
- KPIs de negócio: gasto total, ticket médio, top fornecedores, categorias
- Alertas inteligentes: estoque crítico, anomalias de valor, concentração de fornecedor
- Dashboard interativo com filtros de período no Power BI
- Relatório Excel automatizado com 6 abas e gráficos embutidos

---

## 📧 Contato

**Kleber** — [GitHub](https://github.com/DataKleber)

---

> 💡 *Projeto desenvolvido para demonstrar capacidade de trabalhar em toda a cadeia de dados:*  
> *da simulação de dados brutos até o dashboard executivo — unindo visão de negócio e engenharia.*
