"""
email_service.py — Automação de Compras
Envia o relatório Excel automaticamente via Outlook (win32com)
Uso:
    python email_service.py                  → envia o relatório mais recente
    python email_service.py caminho.xlsx     → envia um arquivo específico
"""

import os
import sys
import glob
from datetime import datetime


# ── Configurações — edite aqui ────────────────────────────────────────────────
DESTINATARIOS = [
    "kleberxcarvalho@yahoo.com.br",       # ← troque pelo email real
    # "gestor@empresa.com",        # adicione mais destinatários se quiser
]

CC = [
    # "diretor@empresa.com",       # com cópia (opcional)
]

RELATORIOS = "relatorios"


# ── Montar corpo do email ──────────────────────────────────────────────────────
def montar_corpo(kpis: dict) -> str:
    return f"""
<html>
<body style="font-family: Arial, sans-serif; color: #1e1e1e; padding: 20px;">

  <h2 style="color: #1E3A5F; border-bottom: 2px solid #2563EB; padding-bottom: 8px;">
    🛒 Relatório Automático de Compras
  </h2>

  <p>Olá,</p>
  <p>Segue em anexo o relatório de compras gerado automaticamente em
     <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong>.</p>

  <h3 style="color: #1E3A5F; margin-top: 24px;">📊 Resumo dos KPIs</h3>

  <table style="border-collapse: collapse; width: 100%; max-width: 560px;">
    <tr style="background-color: #1E3A5F; color: white;">
      <th style="padding: 10px 14px; text-align: left;">Indicador</th>
      <th style="padding: 10px 14px; text-align: right;">Valor</th>
    </tr>
    <tr style="background-color: #EFF6FF;">
      <td style="padding: 9px 14px;">💰 Total Gasto</td>
      <td style="padding: 9px 14px; text-align: right; font-weight: bold;">
          {kpis.get('total_gasto', 'N/A')}
      </td>
    </tr>
    <tr>
      <td style="padding: 9px 14px;">📋 Total de Pedidos</td>
      <td style="padding: 9px 14px; text-align: right; font-weight: bold;">
          {kpis.get('total_pedidos', 'N/A')}
      </td>
    </tr>
    <tr style="background-color: #EFF6FF;">
      <td style="padding: 9px 14px;">🎯 Ticket Médio</td>
      <td style="padding: 9px 14px; text-align: right; font-weight: bold;">
          {kpis.get('ticket_medio', 'N/A')}
      </td>
    </tr>
    <tr>
      <td style="padding: 9px 14px;">🏭 Fornecedores Ativos</td>
      <td style="padding: 9px 14px; text-align: right; font-weight: bold;">
          {kpis.get('total_fornecedores', 'N/A')}
      </td>
    </tr>
    <tr style="background-color: #FEE2E2;">
      <td style="padding: 9px 14px;">⚠️ Estoque Crítico</td>
      <td style="padding: 9px 14px; text-align: right; font-weight: bold; color: #DC2626;">
          {kpis.get('estoque_critico', 'N/A')}
      </td>
    </tr>
    <tr style="background-color: #EFF6FF;">
      <td style="padding: 9px 14px;">📅 Período</td>
      <td style="padding: 9px 14px; text-align: right;">
          {kpis.get('periodo', 'N/A')}
      </td>
    </tr>
  </table>

  <p style="margin-top: 24px; color: #555; font-size: 13px;">
    O relatório completo com gráficos, estoque crítico e detalhamento
    por fornecedor e categoria está em anexo (.xlsx).
  </p>

  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
  <p style="color: #888; font-size: 11px;">
    📧 Email gerado automaticamente pelo sistema de Automação de Compras.<br>
    Não responda este email.
  </p>

</body>
</html>
"""


# ── Buscar KPIs do banco ───────────────────────────────────────────────────────
def buscar_kpis() -> dict:
    try:
        import os
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        from sqlalchemy import create_engine, text

        url = (
            f"postgresql://{os.getenv('DB_USER', 'postgres')}"
            f":{os.getenv('DB_PASSWORD', 'postgres123')}"
            f"@{os.getenv('DB_HOST', 'localhost')}"
            f":{os.getenv('DB_PORT', '5432')}"
            f"/{os.getenv('DB_NAME', 'automacao-compras')}"
        )
        engine = create_engine(url, echo=False)

        with engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM vw_kpis")).fetchone()
            criticos = conn.execute(
                text("SELECT COUNT(*) FROM vw_estoque_critico")
            ).scalar()

        return {
            "total_gasto":        f"R$ {float(row[0]):,.2f}",
            "total_pedidos":      f"{int(row[1]):,}",
            "ticket_medio":       f"R$ {float(row[2]):,.2f}",
            "total_fornecedores": f"{int(row[3]):,}",
            "estoque_critico":    f"{criticos} produtos",
            "periodo":            f"{row[5]} → {row[6]}",
        }
    except Exception as e:
        print(f"  ⚠️  Não foi possível buscar KPIs do banco: {e}")
        return {
            "total_gasto":        "Consulte o relatório em anexo",
            "total_pedidos":      "—",
            "ticket_medio":       "—",
            "total_fornecedores": "—",
            "estoque_critico":    "—",
            "periodo":            "—",
        }


# ── Enviar via Outlook ─────────────────────────────────────────────────────────
def enviar(arquivo: str = None):
    print("\n📧 Iniciando envio do relatório por email...")

    # Localizar relatório mais recente se não especificado
    if not arquivo:
        arquivos = sorted(
            glob.glob(os.path.join(RELATORIOS, "relatorio_compras_*.xlsx")),
            key=os.path.getmtime,
            reverse=True
        )
        if not arquivos:
            print("  ❌ Nenhum relatório encontrado em relatorios/")
            print("     Execute primeiro: python analise.py")
            return False
        arquivo = arquivos[0]

    arquivo = os.path.abspath(arquivo)
    if not os.path.exists(arquivo):
        print(f"  ❌ Arquivo não encontrado: {arquivo}")
        return False

    print(f"  📎 Anexo: {os.path.basename(arquivo)}")
    print(f"  📬 Para: {', '.join(DESTINATARIOS)}")

    # Buscar KPIs para o corpo do email
    kpis = buscar_kpis()

    try:
        import win32com.client as win32
    except ImportError:
        print("\n  ❌ pywin32 não está instalado.")
        print("     Execute: pip install pywin32")
        print("     Depois:  python -m pywin32_postinstall -install")
        return False

    try:
        outlook = win32.Dispatch("outlook.application")
        mail    = outlook.CreateItem(0)  # 0 = MailItem

        mail.Subject = (
            f"📊 Relatório de Compras — "
            f"{datetime.now().strftime('%d/%m/%Y')}"
        )
        mail.HTMLBody  = montar_corpo(kpis)
        mail.Attachments.Add(arquivo)

        for dest in DESTINATARIOS:
            mail.Recipients.Add(dest).Type = 1  # To

        for cc in CC:
            mail.Recipients.Add(cc).Type   = 2  # CC

        mail.Recipients.ResolveAll()
        mail.Send()

        print(f"  ✅ Email enviado com sucesso!")
        print(f"  📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        return True

    except Exception as e:
        print(f"\n  ❌ Erro ao enviar email: {e}")
        print("\n  💡 Verifique:")
        print("     1. O Outlook está aberto e logado")
        print("     2. O email em DESTINATARIOS está preenchido")
        print("     3. pywin32 está instalado corretamente")
        return False


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    arquivo = sys.argv[1] if len(sys.argv) > 1 else None
    sucesso = enviar(arquivo)
    sys.exit(0 if sucesso else 1)