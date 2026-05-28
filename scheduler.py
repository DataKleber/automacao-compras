"""
scheduler.py — Orquestrador do pipeline completo
Automação de Compras | Portfolio: Analista + Engenheiro de Dados

Agenda:
  - Todo dia às 08:00 → simula ERP + carrega banco + gera análise + verifica alertas
  - Toda segunda às 08:05 → envia relatório semanal por email
"""

import schedule
import time
import logging
from datetime import datetime

# ─── Configura log ────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="scheduler.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

def log_print(msg):
    print(msg)
    log.info(msg)

# ─────────────────────────────────────────────
#  JOBS
# ─────────────────────────────────────────────
def job_pipeline_diario():
    """Roda todo dia às 08:00 — simula ERP → carrega banco → analisa → alertas."""
    log_print(f"\n{'='*55}")
    log_print(f"  ⏰  PIPELINE DIÁRIO — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log_print(f"{'='*55}")

    try:
        # 1. Simula ERP (gera compras do dia)
        log_print("\n[1/3] 🏭 Simulando dados do ERP...")
        from simulador import simular_dia
        qtd, valor = simular_dia()
        log_print(f"      ✅ {qtd} pedidos gerados | R$ {valor:,.2f}")

        # 2. Gera análises e relatório Excel
        log_print("\n[2/3] 📊 Gerando análises e relatório Excel...")
        import analise
        analise.main()
        log_print("      ✅ Relatório gerado em relatorios/")

        # 3. Verifica alertas
        log_print("\n[3/3] 🔔 Verificando alertas...")
        from alertas import verificar_alertas
        alertas = verificar_alertas(enviar=True)
        log_print(f"      ✅ {len(alertas)} alerta(s) verificado(s)")

        log_print(f"\n✅ Pipeline diário concluído — {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        log_print(f"\n❌ Erro no pipeline diário: {e}")
        log.exception("Erro no pipeline diário")


def job_email_semanal():
    """Roda toda segunda às 08:05 — envia relatório semanal por email."""
    log_print(f"\n{'='*55}")
    log_print(f"  📧  EMAIL SEMANAL — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log_print(f"{'='*55}")

    try:
        from email_service import enviar_relatorio_semanal
        enviar_relatorio_semanal()
        log_print("✅ Relatório semanal enviado!")
    except Exception as e:
        log_print(f"❌ Erro no email semanal: {e}")
        log.exception("Erro no email semanal")


# ─────────────────────────────────────────────
#  AGENDAMENTO
# ─────────────────────────────────────────────
def iniciar_scheduler():
    print(f"""
{'='*55}
  ⏰  SCHEDULER — Automação de Compras
  📅  Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}
{'='*55}
  📋 Agenda configurada:
     ├─ 08:00 todo dia     → Pipeline completo (ERP + banco + análise + alertas)
     └─ 08:05 toda segunda → Email semanal para gestores

  💡 Para rodar agora:
     python scheduler.py --agora

  🛑 Para parar: Ctrl+C
{'='*55}
""")

    # Agenda os jobs
    schedule.every().day.at("08:00").do(job_pipeline_diario)
    schedule.every().monday.at("08:05").do(job_email_semanal)

    log_print("Scheduler iniciado. Aguardando próxima execução...")

    while True:
        schedule.run_pending()
        time.sleep(30)  # verifica a cada 30 segundos


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--agora" in sys.argv:
        # Executa imediatamente (útil para testar)
        print("🚀 Executando pipeline agora...")
        job_pipeline_diario()
        if datetime.today().weekday() == 0:  # segunda-feira
            job_email_semanal()
    else:
        iniciar_scheduler()