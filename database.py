"""
database.py — Automação de Compras
Carga de 1M+ registros no PostgreSQL via chunks manuais
Dia 3 — Projeto Automação de Compras
"""

import os
import time
import pandas as pd

# ── Carregar variáveis de ambiente ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── String de conexão a partir do .env ────────────────────────────────────────
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER', 'postgres')}"
    f":{os.getenv('DB_PASSWORD', 'postgres123')}"
    f"@{os.getenv('DB_HOST', 'localhost')}"
    f":{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME', 'automacao-compras')}"
)

DADOS      = "dados"
CHUNK_SIZE = 50_000


# ── Conexão ────────────────────────────────────────────────────────────────────
def get_engine():
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("🔌 Conexão com PostgreSQL estabelecida!")
        return engine
    except ImportError:
        raise ImportError("Execute: pip install sqlalchemy psycopg2-binary")
    except Exception as e:
        raise ConnectionError(
            f"\n❌ Falha na conexão: {e}"
            f"\n\n💡 Verifique:"
            f"\n   1. PostgreSQL está rodando (services.msc)"
            f"\n   2. Senha correta no arquivo .env"
            f"\n   3. Banco 'automacao-compras' foi criado"
        )


# ── Schema ─────────────────────────────────────────────────────────────────────
def criar_schema(engine):
    from sqlalchemy import text
    print("\n📐 Criando schema (tabelas, índices e views)...")

    stmts = [
        "DROP TABLE IF EXISTS compras CASCADE",
        "DROP TABLE IF EXISTS produtos CASCADE",
        "DROP TABLE IF EXISTS fornecedores CASCADE",

        """CREATE TABLE fornecedores (
            id                  SERIAL PRIMARY KEY,
            id_fornecedor       INT,
            nome                VARCHAR(150) NOT NULL,
            cnpj                VARCHAR(20),
            contato             VARCHAR(100),
            telefone            VARCHAR(25),
            estado              VARCHAR(2),
            cidade              VARCHAR(100),
            prazo_dias          INT,
            avaliacao           NUMERIC(3,1),
            categoria_principal VARCHAR(50),
            ativo               BOOLEAN DEFAULT TRUE,
            desde               DATE
        )""",

        """CREATE TABLE produtos (
            id                  SERIAL PRIMARY KEY,
            id_produto          INT,
            nome                VARCHAR(150) NOT NULL,
            categoria           VARCHAR(50),
            unidade             VARCHAR(10),
            estoque_atual       INT,
            estoque_minimo      INT,
            estoque_maximo      INT,
            preco_unitario      NUMERIC(12,2),
            valor_em_estoque    NUMERIC(15,2),
            status              VARCHAR(20),
            ultima_atualizacao  DATE,
            fornecedor_id       INT,
            giro_dias           INT
        )""",

        """CREATE TABLE compras (
            id              BIGSERIAL PRIMARY KEY,
            id_pedido       BIGINT,
            produto         VARCHAR(150),
            id_produto      INT,
            categoria       VARCHAR(50),
            fornecedor      VARCHAR(150),
            id_fornecedor   INT,
            quantidade      INT,
            valor_unitario  NUMERIC(12,2),
            valor_total     NUMERIC(15,2),
            data_compra     DATE,
            ano             INT,
            mes             VARCHAR(7),
            trimestre       VARCHAR(8),
            centro_custo    VARCHAR(50),
            status_pedido   VARCHAR(30),
            forma_pagamento VARCHAR(30),
            prazo_pagamento INT,
            nf_numero       VARCHAR(20)
        )""",

        "CREATE INDEX idx_compras_data       ON compras(data_compra)",
        "CREATE INDEX idx_compras_fornecedor ON compras(fornecedor)",
        "CREATE INDEX idx_compras_categoria  ON compras(categoria)",
        "CREATE INDEX idx_compras_ano_mes    ON compras(ano, mes)",
        "CREATE INDEX idx_compras_centro     ON compras(centro_custo)",

        """CREATE OR REPLACE VIEW vw_gastos_fornecedor AS
           SELECT fornecedor, id_fornecedor,
                  SUM(valor_total)                     AS total_gasto,
                  COUNT(*)                             AS qtd_pedidos,
                  ROUND(AVG(valor_total)::NUMERIC, 2)  AS ticket_medio,
                  MIN(data_compra)                     AS primeira_compra,
                  MAX(data_compra)                     AS ultima_compra
           FROM compras
           GROUP BY fornecedor, id_fornecedor
           ORDER BY total_gasto DESC""",

        """CREATE OR REPLACE VIEW vw_compras_mensais AS
           SELECT mes, ano,
                  SUM(valor_total)                     AS total,
                  COUNT(*)                             AS qtd_pedidos,
                  ROUND(AVG(valor_total)::NUMERIC, 2)  AS ticket_medio
           FROM compras
           GROUP BY mes, ano
           ORDER BY mes""",

        """CREATE OR REPLACE VIEW vw_compras_categoria AS
           SELECT categoria,
                  SUM(valor_total)  AS total_gasto,
                  COUNT(*)          AS qtd_pedidos,
                  SUM(quantidade)   AS total_itens
           FROM compras
           GROUP BY categoria
           ORDER BY total_gasto DESC""",

        """CREATE OR REPLACE VIEW vw_estoque_critico AS
           SELECT nome, categoria, unidade,
                  estoque_atual, estoque_minimo,
                  (estoque_minimo - estoque_atual)     AS deficit,
                  preco_unitario,
                  ROUND(
                      (estoque_atual::NUMERIC / NULLIF(estoque_minimo,0) * 100), 1
                  )                                    AS pct_minimo
           FROM produtos
           WHERE estoque_atual <= estoque_minimo
           ORDER BY deficit DESC""",

        """CREATE OR REPLACE VIEW vw_kpis AS
           SELECT
               SUM(valor_total)                        AS total_gasto,
               COUNT(*)                                AS total_pedidos,
               ROUND(AVG(valor_total)::NUMERIC, 2)     AS ticket_medio,
               COUNT(DISTINCT fornecedor)              AS total_fornecedores,
               COUNT(DISTINCT categoria)               AS total_categorias,
               MIN(data_compra)                        AS data_inicio,
               MAX(data_compra)                        AS data_fim
           FROM compras""",
    ]

    with engine.connect() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.commit()

    print("  ✅ Tabelas criadas: compras, produtos, fornecedores")
    print("  ✅ Índices e views criados")


# ── Barra de progresso ─────────────────────────────────────────────────────────
def _barra(atual, total, largura=35):
    pct   = min(atual / total, 1.0)
    cheio = int(pct * largura)
    bar   = "█" * cheio + "░" * (largura - cheio)
    return f"  [{bar}] {pct*100:.0f}% ({atual:,}/{total:,})"


# ── Carga: Fornecedores ────────────────────────────────────────────────────────
def carregar_fornecedores(engine):
    print("\n🏭 Carregando fornecedores...")
    t0 = time.time()
    caminho = os.path.join(DADOS, "fornecedores_1k.xlsx")
    if not os.path.exists(caminho):
        print(f"  ⚠️  Não encontrado: {caminho}"); return

    df = pd.read_excel(caminho)
    df.columns = [c.lower().replace(" ","_").replace("(","").replace(")","") for c in df.columns]
    df = df.rename(columns={"fornecedor": "nome", "prazo_entrega_dias": "prazo_dias"})
    if "ativo" in df.columns:
        df["ativo"] = df["ativo"].map({"Sim": True, "Não": False, "sim": True, "não": False,
                                        True: True, False: False})
    df.to_sql("fornecedores", engine, if_exists="append", index=False, method="multi", chunksize=500)
    print(f"  ✅ {len(df):,} fornecedores inseridos em {time.time()-t0:.1f}s")


# ── Carga: Estoque ─────────────────────────────────────────────────────────────
def carregar_estoque(engine):
    print("\n📦 Carregando estoque...")
    t0 = time.time()
    caminho = os.path.join(DADOS, "estoque_10k.xlsx")
    if not os.path.exists(caminho):
        print(f"  ⚠️  Não encontrado: {caminho}"); return

    df = pd.read_excel(caminho)
    df.columns = [c.lower().replace(" ","_") for c in df.columns]
    df = df.rename(columns={"produto": "nome", "giro_(dias)": "giro_dias"})
    df.to_sql("produtos", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"  ✅ {len(df):,} produtos inseridos em {time.time()-t0:.1f}s")


# ── Carga: Compras (leitura completa + chunks manuais) ────────────────────────
def carregar_compras(engine):
    print("\n🛒 Carregando 1.000.000 compras...")
    print("  ⏳ Lendo o Excel completo — aguarde (2 a 5 min para ler o arquivo)...")

    caminho = os.path.join(DADOS, "compras_1M.xlsx")
    if not os.path.exists(caminho):
        print(f"  ⚠️  Não encontrado: {caminho}"); return

    t0 = time.time()

    col_map = {
        "ID Pedido":       "id_pedido",
        "Produto":         "produto",
        "ID Produto":      "id_produto",
        "Categoria":       "categoria",
        "Fornecedor":      "fornecedor",
        "ID Fornecedor":   "id_fornecedor",
        "Quantidade":      "quantidade",
        "Valor Unitario":  "valor_unitario",
        "Valor Total":     "valor_total",
        "Data":            "data_compra",
        "Ano":             "ano",
        "Mes":             "mes",
        "Trimestre":       "trimestre",
        "Centro de Custo": "centro_custo",
        "Status Pedido":   "status_pedido",
        "Forma Pagamento": "forma_pagamento",
        "Prazo Pagamento": "prazo_pagamento",
        "NF Numero":       "nf_numero",
    }

    # read_excel não suporta chunksize — lê tudo e fatia manualmente
    df = pd.read_excel(caminho)
    df = df.rename(columns=col_map)

    if "data_compra" in df.columns:
        df["data_compra"] = pd.to_datetime(df["data_compra"], errors="coerce").dt.date

    total = len(df)
    leitura_min = (time.time() - t0) / 60
    print(f"  ✅ Arquivo lido: {total:,} linhas em {leitura_min:.1f} min")
    print(f"  📤 Inserindo no banco em chunks de {CHUNK_SIZE:,}...\n")

    inseridos = 0
    for inicio in range(0, total, CHUNK_SIZE):
        chunk = df.iloc[inicio : inicio + CHUNK_SIZE]
        chunk.to_sql("compras", engine, if_exists="append", index=False,
                     method="multi", chunksize=5000)
        inseridos += len(chunk)
        elapsed = time.time() - t0
        print(f"\r{_barra(inseridos, total)}  {elapsed:.0f}s", end="", flush=True)

    print(f"\n  ✅ {inseridos:,} compras inseridas em {(time.time()-t0)/60:.1f} minutos!")


# ── KPIs ───────────────────────────────────────────────────────────────────────
def consultar_kpis(engine):
    from sqlalchemy import text
    print("\n" + "="*55)
    print("  📊 KPIs DIRETO DO POSTGRESQL")
    print("="*55)

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM vw_kpis")).fetchone()
        print(f"  💰 Total Gasto:          R$ {float(row[0]):>20,.2f}")
        print(f"  📋 Total de Pedidos:     {int(row[1]):>23,}")
        print(f"  🎯 Ticket Médio:         R$ {float(row[2]):>20,.2f}")
        print(f"  🏭 Fornecedores:         {int(row[3]):>23,}")
        print(f"  📦 Categorias:           {int(row[4]):>23,}")
        print(f"  📅 Período:              {str(row[5])} → {str(row[6])}")

        print("\n  🏆 Top 5 Fornecedores:")
        rows = conn.execute(text(
            "SELECT fornecedor, total_gasto, qtd_pedidos FROM vw_gastos_fornecedor LIMIT 5"
        )).fetchall()
        for i, r in enumerate(rows, 1):
            nome = str(r[0])[:38].ljust(38)
            print(f"     {i}. {nome}  R$ {float(r[1]):>15,.2f}  ({int(r[2]):,} pedidos)")

        print("\n  📦 Top 5 Categorias:")
        rows = conn.execute(text(
            "SELECT categoria, total_gasto FROM vw_compras_categoria LIMIT 5"
        )).fetchall()
        for i, r in enumerate(rows, 1):
            cat = str(r[0])[:25].ljust(25)
            print(f"     {i}. {cat}  R$ {float(r[1]):>15,.2f}")

        criticos = conn.execute(text("SELECT COUNT(*) FROM vw_estoque_critico")).scalar()
        print(f"\n  ⚠️  Produtos estoque crítico: {criticos}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("  🗄️  DIA 3 — Carga PostgreSQL | Automação de Compras")
    print("="*55)
    t_total = time.time()

    try:
        engine = get_engine()
        criar_schema(engine)
        carregar_fornecedores(engine)
        carregar_estoque(engine)
        carregar_compras(engine)
        consultar_kpis(engine)

        total_min = (time.time() - t_total) / 60
        print(f"\n{'='*55}")
        print(f"  ✅ CONCLUÍDO em {total_min:.1f} minutos!")
        print(f"  🚀 Banco pronto para o Power BI!")
        print(f"{'='*55}")

    except ConnectionError as e:
        print(e)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()