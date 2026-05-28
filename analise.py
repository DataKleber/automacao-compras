"""
analise.py — Automação de Compras
Gera KPIs, 4 gráficos e relatório Excel com 6 abas
"""

import os
import warnings
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import datetime
from sqlalchemy import create_engine, text

warnings.filterwarnings("ignore")

# ── Conexão ────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER', 'postgres')}"
    f":{os.getenv('DB_PASSWORD', 'postgres123')}"
    f"@{os.getenv('DB_HOST', 'localhost')}"
    f":{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME', 'automacao-compras')}"
)

RELATORIOS = "relatorios"
os.makedirs(RELATORIOS, exist_ok=True)


def get_engine():
    engine = create_engine(DATABASE_URL, echo=False)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("🔌 Conexão com PostgreSQL estabelecida!")
    return engine


# ── Carregar dados do banco ────────────────────────────────────────────────────
def carregar_dados(engine):
    print("📥 Carregando dados do banco...")

    compras = pd.read_sql("""
        SELECT id_pedido, produto, categoria, fornecedor,
               quantidade, valor_unitario, valor_total,
               data_compra, ano, mes, trimestre,
               centro_custo, status_pedido, forma_pagamento
        FROM compras
    """, engine)

    estoque = pd.read_sql("""
        SELECT nome, categoria, unidade,
               estoque_atual, estoque_minimo, estoque_maximo,
               preco_unitario, valor_em_estoque, status, giro_dias
        FROM produtos
    """, engine)

    fornecedores = pd.read_sql("""
        SELECT nome, cnpj, cidade, estado,
               avaliacao, prazo_dias, categoria_principal, ativo
        FROM fornecedores
    """, engine)

    kpis = pd.read_sql("SELECT * FROM vw_kpis", engine)
    gastos_forn = pd.read_sql("SELECT * FROM vw_gastos_fornecedor", engine)
    compras_mens = pd.read_sql("SELECT * FROM vw_compras_mensais ORDER BY ano, mes", engine)
    compras_cat = pd.read_sql("SELECT * FROM vw_compras_categoria", engine)
    estoque_crit = pd.read_sql("SELECT * FROM vw_estoque_critico", engine)

    print(f"  ✅ {len(compras):,} compras | {len(estoque):,} produtos | {len(fornecedores):,} fornecedores")
    return compras, estoque, fornecedores, kpis, gastos_forn, compras_mens, compras_cat, estoque_crit


# ── Gráficos ───────────────────────────────────────────────────────────────────
CORES = ["#2563EB", "#16A34A", "#DC2626", "#D97706", "#7C3AED",
         "#0891B2", "#DB2777", "#65A30D"]

def fmt_bilhoes(x, _):
    if x >= 1e9:  return f"R$ {x/1e9:.1f}Bi"
    if x >= 1e6:  return f"R$ {x/1e6:.0f}Mi"
    return f"R$ {x:,.0f}"


def grafico_gastos_fornecedor(gastos_forn):
    print("  📊 Gráfico 1: Gastos por Fornecedor")
    top = gastos_forn.head(12).sort_values("total_gasto")

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(top["fornecedor"], top["total_gasto"], color=CORES[0], edgecolor="white")

    for bar in bars:
        w = bar.get_width()
        ax.text(w * 1.01, bar.get_y() + bar.get_height()/2,
                fmt_bilhoes(w, None), va="center", fontsize=8)

    ax.set_title("Top 12 Fornecedores por Gasto Total", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Total Gasto (R$)", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_bilhoes))
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()

    path = os.path.join(RELATORIOS, "01_gastos_fornecedor.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def grafico_compras_mensais(compras_mens):
    print("  📈 Gráfico 2: Compras Mensais")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(range(len(compras_mens)), compras_mens["total"],
            color=CORES[0], linewidth=2.5, marker="o", markersize=4)
    ax.fill_between(range(len(compras_mens)), compras_mens["total"],
                    alpha=0.15, color=CORES[0])

    # Labels de ano no eixo X
    anos = compras_mens.groupby("ano").first().reset_index()
    ticks = []
    for _, row in anos.iterrows():
        idx = compras_mens[compras_mens["ano"] == row["ano"]].index[0]
        ticks.append((list(compras_mens.index).index(idx), str(row["ano"])))

    ax.set_xticks([t[0] for t in ticks])
    ax.set_xticklabels([t[1] for t in ticks])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_bilhoes))
    ax.set_title("Evolução de Compras Mensais (2018–2024)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Total Gasto (R$)", fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()

    path = os.path.join(RELATORIOS, "02_compras_mensais.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def grafico_categoria(compras_cat):
    print("  🍩 Gráfico 3: Gastos por Categoria")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Pizza
    ax = axes[0]
    wedges, texts, autotexts = ax.pie(
        compras_cat["total_gasto"],
        labels=compras_cat["categoria"],
        autopct="%1.1f%%",
        colors=CORES[:len(compras_cat)],
        startangle=140,
        pctdistance=0.82
    )
    for t in autotexts: t.set_fontsize(9)
    ax.set_title("Distribuição por Categoria", fontsize=13, fontweight="bold")

    # Barras
    ax2 = axes[1]
    cat_sorted = compras_cat.sort_values("total_gasto")
    bars = ax2.barh(cat_sorted["categoria"], cat_sorted["total_gasto"],
                    color=CORES[:len(cat_sorted)])
    for bar in bars:
        w = bar.get_width()
        ax2.text(w * 1.01, bar.get_y() + bar.get_height()/2,
                 fmt_bilhoes(w, None), va="center", fontsize=9)
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_bilhoes))
    ax2.set_title("Gasto Total por Categoria", fontsize=13, fontweight="bold")
    ax2.spines[["top","right"]].set_visible(False)
    ax2.grid(axis="x", linestyle="--", alpha=0.4)

    fig.tight_layout()
    path = os.path.join(RELATORIOS, "03_gastos_categoria.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def grafico_estoque_critico(estoque_crit):
    print("  ⚠️  Gráfico 4: Estoque Crítico")

    top = estoque_crit.head(15).sort_values("deficit")

    fig, ax = plt.subplots(figsize=(12, 7))
    cores = ["#DC2626" if d > 40 else "#D97706" if d > 20 else "#F59E0B"
             for d in top["deficit"]]
    bars = ax.barh(top["nome"], top["deficit"], color=cores, edgecolor="white")

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.3, bar.get_y() + bar.get_height()/2,
                f"{int(w)} un.", va="center", fontsize=8)

    ax.set_title("Top 15 Produtos com Maior Déficit de Estoque", fontsize=14,
                 fontweight="bold", pad=15)
    ax.set_xlabel("Déficit (unidades abaixo do mínimo)", fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    from matplotlib.patches import Patch
    legenda = [Patch(color="#DC2626", label="Crítico (>40)"),
               Patch(color="#D97706", label="Alerta (20-40)"),
               Patch(color="#F59E0B", label="Atenção (<20)")]
    ax.legend(handles=legenda, loc="lower right", fontsize=9)

    fig.tight_layout()
    path = os.path.join(RELATORIOS, "04_estoque_critico.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Relatório Excel — 6 abas ───────────────────────────────────────────────────
def gerar_relatorio(compras, estoque, fornecedores, kpis,
                    gastos_forn, compras_mens, compras_cat, estoque_crit,
                    graficos):
    print("\n📄 Gerando relatório Excel com 6 abas...")

    data_hoje = datetime.now().strftime("%Y%m%d_%H%M")
    nome_arquivo = os.path.join(RELATORIOS, f"relatorio_compras_{data_hoje}.xlsx")

    row = kpis.iloc[0]

    with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
        wb = writer.book

        # ── ABA 1: KPIs ───────────────────────────────────────────────────────
        from openpyxl.styles import (Font, PatternFill, Alignment,
                                     Border, Side, numbers)
        from openpyxl.utils import get_column_letter
        from openpyxl import load_workbook
        import openpyxl

        ws_kpi = wb.create_sheet("📊 KPIs", 0)

        # Cabeçalho
        ws_kpi.merge_cells("A1:F1")
        c = ws_kpi["A1"]
        c.value = "RELATÓRIO DE KPIs — AUTOMAÇÃO DE COMPRAS"
        c.font = Font(bold=True, size=16, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E3A5F")
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws_kpi.row_dimensions[1].height = 35

        ws_kpi.merge_cells("A2:F2")
        c2 = ws_kpi["A2"]
        c2.value = f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | Período: {row['data_inicio']} → {row['data_fim']}"
        c2.font = Font(italic=True, size=10, color="555555")
        c2.alignment = Alignment(horizontal="center")

        # Cards KPI
        kpi_data = [
            ("💰 Total Gasto",        f"R$ {float(row['total_gasto']):,.2f}",      "1E3A5F"),
            ("📋 Total de Pedidos",   f"{int(row['total_pedidos']):,}",             "16A34A"),
            ("🎯 Ticket Médio",       f"R$ {float(row['ticket_medio']):,.2f}",      "2563EB"),
            ("🏭 Fornecedores",       f"{int(row['total_fornecedores']):,}",        "7C3AED"),
            ("📦 Categorias",         f"{int(row['total_categorias']):,}",          "D97706"),
            ("⚠️ Estoque Crítico",    f"{len(estoque_crit):,} produtos",            "DC2626"),
        ]

        thin = Side(style="thin", color="CCCCCC")
        borda = Border(left=thin, right=thin, top=thin, bottom=thin)

        for i, (label, valor, cor) in enumerate(kpi_data):
            col = i + 1
            letra = get_column_letter(col)
            ws_kpi.column_dimensions[letra].width = 22

            cl = ws_kpi.cell(row=4, column=col, value=label)
            cl.font = Font(bold=True, size=10, color="FFFFFF")
            cl.fill = PatternFill("solid", fgColor=cor)
            cl.alignment = Alignment(horizontal="center", vertical="center")
            cl.border = borda
            ws_kpi.row_dimensions[4].height = 25

            cv = ws_kpi.cell(row=5, column=col, value=valor)
            cv.font = Font(bold=True, size=13, color=cor)
            cv.alignment = Alignment(horizontal="center", vertical="center")
            cv.border = borda
            ws_kpi.row_dimensions[5].height = 30

        # Top 10 Fornecedores
        ws_kpi.cell(row=7, column=1, value="🏆 TOP 10 FORNECEDORES").font = Font(bold=True, size=12)
        headers = ["Fornecedor", "Total Gasto (R$)", "Qtd Pedidos", "Ticket Médio (R$)",
                   "Primeira Compra", "Última Compra"]
        for j, h in enumerate(headers, 1):
            c = ws_kpi.cell(row=8, column=j, value=h)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="2563EB")
            c.alignment = Alignment(horizontal="center")
            c.border = borda

        for i, (_, r) in enumerate(gastos_forn.head(10).iterrows(), 9):
            vals = [r["fornecedor"], float(r["total_gasto"]), int(r["qtd_pedidos"]),
                    float(r["ticket_medio"]), str(r["primeira_compra"]), str(r["ultima_compra"])]
            for j, v in enumerate(vals, 1):
                c = ws_kpi.cell(row=i, column=j, value=v)
                c.border = borda
                if i % 2 == 0:
                    c.fill = PatternFill("solid", fgColor="EFF6FF")

        # ── ABA 2: Compras ────────────────────────────────────────────────────
        sample = compras.head(100000)  # 100k linhas para não travar Excel
        sample.to_excel(writer, sheet_name="📦 Compras", index=False)
        ws_c = writer.sheets["📦 Compras"]
        for cell in ws_c[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1E3A5F")
            cell.alignment = Alignment(horizontal="center")

        # ── ABA 3: Estoque ────────────────────────────────────────────────────
        estoque.to_excel(writer, sheet_name="🏪 Estoque", index=False)
        ws_e = writer.sheets["🏪 Estoque"]
        for cell in ws_e[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="16A34A")
            cell.alignment = Alignment(horizontal="center")

        # Colorir críticos em vermelho
        for row_e in ws_e.iter_rows(min_row=2, max_row=ws_e.max_row):
            status_cell = row_e[8] if len(row_e) > 8 else None
            if status_cell and str(status_cell.value) in ("Crítico", "Abaixo do Mínimo"):
                for cell in row_e:
                    cell.fill = PatternFill("solid", fgColor="FEE2E2")

        # ── ABA 4: Fornecedores ───────────────────────────────────────────────
        fornecedores.to_excel(writer, sheet_name="🏭 Fornecedores", index=False)
        ws_f = writer.sheets["🏭 Fornecedores"]
        for cell in ws_f[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="7C3AED")
            cell.alignment = Alignment(horizontal="center")

        # ── ABA 5: Gráficos ───────────────────────────────────────────────────
        ws_g = wb.create_sheet("📈 Gráficos")
        ws_g.merge_cells("A1:P1")
        tit = ws_g["A1"]
        tit.value = "DASHBOARDS — AUTOMAÇÃO DE COMPRAS"
        tit.font = Font(bold=True, size=14, color="FFFFFF")
        tit.fill = PatternFill("solid", fgColor="1E3A5F")
        tit.alignment = Alignment(horizontal="center", vertical="center")
        ws_g.row_dimensions[1].height = 30

        from openpyxl.drawing.image import Image as XLImage
        posicoes = ["A2", "I2", "A32", "I32"]
        for path, pos in zip(graficos, posicoes):
            if os.path.exists(path):
                img = XLImage(path)
                img.width  = 480
                img.height = 280
                ws_g.add_image(img, pos)

        # ── ABA 6: SQL Schema ─────────────────────────────────────────────────
        ws_sql = wb.create_sheet("🗄️ SQL Schema")
        schema_text = """-- =====================================================
-- SCHEMA — AUTOMAÇÃO DE COMPRAS
-- Banco: automacao-compras | PostgreSQL
-- =====================================================

-- TABELA: fornecedores
CREATE TABLE fornecedores (
    id                  SERIAL PRIMARY KEY,
    id_fornecedor       INT,
    nome                VARCHAR(150) NOT NULL,
    cnpj                VARCHAR(20),
    cidade              VARCHAR(100),
    estado              VARCHAR(2),
    avaliacao           NUMERIC(3,1),
    prazo_dias          INT,
    categoria_principal VARCHAR(50),
    ativo               BOOLEAN DEFAULT TRUE
);

-- TABELA: produtos (estoque)
CREATE TABLE produtos (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(150) NOT NULL,
    categoria           VARCHAR(50),
    unidade             VARCHAR(10),
    estoque_atual       INT,
    estoque_minimo      INT,
    estoque_maximo      INT,
    preco_unitario      NUMERIC(12,2),
    valor_em_estoque    NUMERIC(15,2),
    status              VARCHAR(20),
    giro_dias           INT
);

-- TABELA: compras (1.000.000 registros)
CREATE TABLE compras (
    id              BIGSERIAL PRIMARY KEY,
    id_pedido       BIGINT,
    produto         VARCHAR(150),
    categoria       VARCHAR(50),
    fornecedor      VARCHAR(150),
    quantidade      INT,
    valor_unitario  NUMERIC(12,2),
    valor_total     NUMERIC(15,2),
    data_compra     DATE,
    ano             INT,
    mes             VARCHAR(7),
    trimestre       VARCHAR(8),
    centro_custo    VARCHAR(50),
    status_pedido   VARCHAR(30),
    forma_pagamento VARCHAR(30)
);

-- ÍNDICES
CREATE INDEX idx_compras_data       ON compras(data_compra);
CREATE INDEX idx_compras_fornecedor ON compras(fornecedor);
CREATE INDEX idx_compras_categoria  ON compras(categoria);
CREATE INDEX idx_compras_ano_mes    ON compras(ano, mes);

-- VIEW: KPIs gerais
CREATE VIEW vw_kpis AS
SELECT
    SUM(valor_total)                    AS total_gasto,
    COUNT(*)                            AS total_pedidos,
    ROUND(AVG(valor_total)::NUMERIC, 2) AS ticket_medio,
    COUNT(DISTINCT fornecedor)          AS total_fornecedores,
    COUNT(DISTINCT categoria)           AS total_categorias,
    MIN(data_compra)                    AS data_inicio,
    MAX(data_compra)                    AS data_fim
FROM compras;

-- VIEW: Gastos por fornecedor
CREATE VIEW vw_gastos_fornecedor AS
SELECT fornecedor,
       SUM(valor_total)  AS total_gasto,
       COUNT(*)          AS qtd_pedidos,
       AVG(valor_total)  AS ticket_medio
FROM compras
GROUP BY fornecedor
ORDER BY total_gasto DESC;

-- VIEW: Compras mensais
CREATE VIEW vw_compras_mensais AS
SELECT mes, ano, SUM(valor_total) AS total, COUNT(*) AS qtd_pedidos
FROM compras
GROUP BY mes, ano
ORDER BY mes;

-- VIEW: Estoque crítico
CREATE VIEW vw_estoque_critico AS
SELECT nome, categoria, estoque_atual, estoque_minimo,
       (estoque_minimo - estoque_atual) AS deficit
FROM produtos
WHERE estoque_atual <= estoque_minimo
ORDER BY deficit DESC;
"""
        for i, linha in enumerate(schema_text.split("\n"), 1):
            c = ws_sql.cell(row=i, column=1, value=linha)
            c.font = Font(name="Courier New", size=9,
                          color="16A34A" if linha.strip().startswith("--") else "1E1E1E")

        ws_sql.column_dimensions["A"].width = 80

    print(f"  ✅ Relatório salvo: {nome_arquivo}")
    return nome_arquivo


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  📊 ANALISE.PY — Relatório de Compras")
    print("=" * 55)

    engine = get_engine()
    compras, estoque, fornecedores, kpis, gastos_forn, \
        compras_mens, compras_cat, estoque_crit = carregar_dados(engine)

    print("\n🎨 Gerando gráficos...")
    graficos = [
        grafico_gastos_fornecedor(gastos_forn),
        grafico_compras_mensais(compras_mens),
        grafico_categoria(compras_cat),
        grafico_estoque_critico(estoque_crit),
    ]

    arquivo = gerar_relatorio(
        compras, estoque, fornecedores, kpis,
        gastos_forn, compras_mens, compras_cat, estoque_crit,
        graficos
    )

    print("\n" + "="*55)
    print("  ✅ CONCLUÍDO!")
    print(f"  📁 Relatório: {arquivo}")
    print(f"  🖼️  Gráficos:  {RELATORIOS}/")
    print("="*55)


if __name__ == "__main__":
    main()