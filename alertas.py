"""
alertas.py — Sistema de alertas inteligentes de negócio
Automação de Compras | Portfolio: Analista + Engenheiro de Dados

Colunas reais do banco:
  fornecedores : id_fornecedor, nome, categoria_principal, ativo
  produtos     : id_produto, nome, categoria, estoque_atual, estoque_minimo, preco_unitario
  compras      : id_pedido, produto, id_produto, categoria, fornecedor, id_fornecedor,
                 quantidade, valor_unitario, valor_total, data_compra, ano, mes,
                 trimestre, centro_custo, status_pedido, forma_pagamento, prazo_pagamento, nf_numero
"""

import os
from datetime import date
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import pandas as pd

load_dotenv()

DESTINATARIOS_ALERTA = [
    "gestor@empresa.com",  # ← troque pelo email real
]

LIMITES = {
    "gasto_diario_max":       500_000,  # R$ 500k/dia dispara alerta
    "ticket_anomalia_mult":       3.0,  # pedido 3x acima do ticket médio
    "fornecedor_concentracao":   0.40,  # 1 fornecedor com > 40% do gasto mensal
}


# ─────────────────────────────────────────────
#  CONEXÃO — retorna engine SQLAlchemy (compatível com pd.read_sql)
# ─────────────────────────────────────────────
def get_engine():
    from sqlalchemy import create_engine
    host   = os.getenv("DB_HOST", "localhost")
    port   = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "automacao-compras")
    user   = os.getenv("DB_USER", "postgres")
    pwd    = os.getenv("DB_PASSWORD", "postgres123")
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}")


# ─────────────────────────────────────────────
#  VERIFICAÇÕES
# ─────────────────────────────────────────────
def verificar_estoque_critico(engine):
    """Produtos com estoque_atual abaixo do estoque_minimo."""
    return pd.read_sql("""
        SELECT id_produto,
               nome            AS produto,
               categoria,
               estoque_atual,
               estoque_minimo,
               ROUND(estoque_atual::numeric
                     / NULLIF(estoque_minimo, 0) * 100, 1) AS pct_estoque
        FROM produtos
        WHERE estoque_atual < estoque_minimo
        ORDER BY pct_estoque ASC
        LIMIT 20
    """, engine)


def verificar_gasto_diario(engine):
    """Gasto total de hoje."""
    df = pd.read_sql("""
        SELECT COALESCE(SUM(valor_total), 0) AS gasto_hoje,
               COUNT(*)                       AS pedidos_hoje
        FROM compras
        WHERE data_compra = CURRENT_DATE
    """, engine)
    gasto   = float(df["gasto_hoje"].iloc[0])
    pedidos = int(df["pedidos_hoje"].iloc[0])
    return gasto, pedidos, gasto > LIMITES["gasto_diario_max"]


def verificar_pedidos_anomalos(engine):
    """Pedidos com valor muito acima do ticket médio (últimos 7 dias)."""
    return pd.read_sql("""
        WITH media AS (
            SELECT AVG(valor_total) AS ticket_medio FROM compras
        )
        SELECT c.id_pedido,
               c.data_compra,
               c.fornecedor,
               c.categoria,
               c.valor_total,
               ROUND(c.valor_total / m.ticket_medio, 1) AS multiplo_medio
        FROM compras c, media m
        WHERE c.valor_total > m.ticket_medio * %(mult)s
          AND c.data_compra >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY c.valor_total DESC
        LIMIT 10
    """, engine, params={"mult": LIMITES["ticket_anomalia_mult"]})


def verificar_concentracao_fornecedor(engine):
    """Fornecedor com participação acima do limite no mês atual."""
    return pd.read_sql("""
        WITH mensal AS (
            SELECT SUM(valor_total) AS total_mes
            FROM compras
            WHERE DATE_TRUNC('month', data_compra) = DATE_TRUNC('month', CURRENT_DATE)
        )
        SELECT c.fornecedor,
               SUM(c.valor_total)                                   AS gasto_forn,
               ROUND(SUM(c.valor_total) / m.total_mes * 100, 1)    AS pct_total
        FROM compras c
        CROSS JOIN mensal m
        WHERE DATE_TRUNC('month', c.data_compra) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY c.fornecedor, m.total_mes
        HAVING SUM(c.valor_total) / m.total_mes > %(conc)s
        ORDER BY pct_total DESC
    """, engine, params={"conc": LIMITES["fornecedor_concentracao"]})


# ─────────────────────────────────────────────
#  RELATÓRIO DE ALERTAS
# ─────────────────────────────────────────────
def gerar_relatorio_alertas(engine):
    hoje = date.today().strftime("%d/%m/%Y")
    alertas = []
    detalhes_html = ""

    # 1. Estoque crítico
    df_est = verificar_estoque_critico(engine)
    if not df_est.empty:
        alertas.append(f"⚠️  {len(df_est)} produtos com estoque crítico")
        detalhes_html += f"""
        <h3 style="color:#e74c3c">⚠️ Estoque Crítico — {len(df_est)} produtos</h3>
        {df_est.to_html(index=False, border=0)}
        """

    # 2. Gasto diário
    gasto, pedidos, disparou = verificar_gasto_diario(engine)
    if disparou:
        alertas.append(
            f"🚨 Gasto diário R$ {gasto:,.0f} acima do limite "
            f"R$ {LIMITES['gasto_diario_max']:,.0f}"
        )
        detalhes_html += f"""
        <h3 style="color:#e74c3c">🚨 Gasto Diário Elevado</h3>
        <p>Hoje: <strong>R$ {gasto:,.2f}</strong> em {pedidos} pedidos</p>
        """
    else:
        detalhes_html += f"""
        <h3 style="color:#27ae60">✅ Gasto Diário Normal</h3>
        <p>R$ {gasto:,.2f} em {pedidos} pedidos</p>
        """

    # 3. Pedidos anômalos
    df_anom = verificar_pedidos_anomalos(engine)
    if not df_anom.empty:
        alertas.append(f"🔍 {len(df_anom)} pedidos anômalos nos últimos 7 dias")
        detalhes_html += f"""
        <h3 style="color:#e67e22">🔍 Pedidos Anômalos (últimos 7 dias)</h3>
        {df_anom.to_html(index=False, border=0)}
        """

    # 4. Concentração de fornecedor
    df_conc = verificar_concentracao_fornecedor(engine)
    if not df_conc.empty:
        alertas.append(
            f"📊 Concentração de fornecedor acima de "
            f"{LIMITES['fornecedor_concentracao']*100:.0f}%"
        )
        detalhes_html += f"""
        <h3 style="color:#8e44ad">📊 Concentração de Fornecedor no Mês</h3>
        {df_conc.to_html(index=False, border=0)}
        """

    resumo = f"{len(alertas)} alerta(s) encontrado(s)" if alertas else "✅ Sem alertas críticos"
    return alertas, detalhes_html, resumo


# ─────────────────────────────────────────────
#  ENVIO DE EMAIL (Outlook)
# ─────────────────────────────────────────────
def enviar_email_alerta(alertas, detalhes_html, resumo):
    if not alertas:
        print("  ℹ️  Nenhum alerta crítico — email não enviado.")
        return

    hoje    = date.today().strftime("%d/%m/%Y")
    assunto = f"[ALERTA] Automação de Compras — {len(alertas)} alertas em {hoje}"
    html    = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
    <h2>🚨 Relatório de Alertas — {hoje}</h2>
    <p><strong>Resumo:</strong> {resumo}</p>
    <ul>{''.join(f'<li>{a}</li>' for a in alertas)}</ul>
    <hr>{detalhes_html}
    </body></html>
    """
    try:
        import win32com.client
        outlook  = win32com.client.Dispatch("Outlook.Application")
        mail     = outlook.CreateItem(0)
        mail.To  = "; ".join(DESTINATARIOS_ALERTA)
        mail.Subject  = assunto
        mail.HTMLBody = html
        mail.Send()
        print(f"  ✅ Email de alerta enviado!")
    except Exception as e:
        print(f"  ⚠️  Email não enviado (Outlook indisponível): {e}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def verificar_alertas(enviar=False):
    print(f"\n{'='*55}")
    print(f"  🔔  VERIFICAÇÃO DE ALERTAS — {date.today().strftime('%d/%m/%Y')}")
    print(f"{'='*55}")

    engine = get_engine()
    alertas, detalhes_html, resumo = gerar_relatorio_alertas(engine)

    if alertas:
        print(f"\n🚨 {len(alertas)} alerta(s) detectado(s):")
        for a in alertas:
            print(f"   {a}")
    else:
        print("\n✅ Nenhum alerta crítico!")

    print(f"\n📋 {resumo}")

    if enviar:
        enviar_email_alerta(alertas, detalhes_html, resumo)

    return alertas


if __name__ == "__main__":
    verificar_alertas(enviar=True)