"""
main.py — Automação de Compras
Ponto de entrada: roda todo o pipeline com 1 comando
  python main.py              → análise + relatório
  python main.py --email      → análise + relatório + envia email
  python main.py --db         → recarrega o banco antes de analisar
  python main.py --db --email → pipeline completo
"""

import sys
import time
from datetime import datetime


def banner():
    print("=" * 55)
    print("  🛒  AUTOMAÇÃO DE COMPRAS — PIPELINE COMPLETO")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)


def passo(numero, total, descricao):
    print(f"\n[{numero}/{total}] {descricao}")
    print("-" * 40)


def main():
    banner()

    args        = sys.argv[1:]
    rodar_db    = "--db"    in args
    rodar_email = "--email" in args

    total_passos = 2 + rodar_db + rodar_email
    passo_atual  = 0
    t_inicio     = time.time()

    # ── Passo opcional: recarregar banco ──────────────────────────────────────
    if rodar_db:
        passo_atual += 1
        passo(passo_atual, total_passos, "🗄️  Carregando dados no PostgreSQL")
        try:
            import importlib.util, os

            spec   = importlib.util.spec_from_file_location(
                "database",
                os.path.join(os.path.dirname(__file__), "database.py")
            )
            db_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_mod)

            # Chama as funções principais do database.py
            engine = db_mod.get_engine()
            db_mod.criar_schema(engine)
            db_mod.carregar_fornecedores(engine)
            db_mod.carregar_estoque(engine)
            db_mod.carregar_compras(engine)
            db_mod.consultar_kpis(engine)

        except Exception as e:
            print(f"❌ Erro no database.py: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # ── Passo: Análise + Relatório ────────────────────────────────────────────
    passo_atual += 1
    passo(passo_atual, total_passos, "📊 Gerando análises, gráficos e relatório Excel")
    try:
        import importlib.util, os

        spec     = importlib.util.spec_from_file_location(
            "analise",
            os.path.join(os.path.dirname(__file__), "analise.py")
        )
        an_mod   = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(an_mod)
        an_mod.main()

    except Exception as e:
        print(f"❌ Erro no analise.py: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Passo: Localizar relatório gerado ─────────────────────────────────────
    passo_atual += 1
    passo(passo_atual, total_passos, "📁 Localizando relatório gerado")
    import os, glob

    arquivos = sorted(
        glob.glob(os.path.join("relatorios", "relatorio_compras_*.xlsx")),
        key=os.path.getmtime,
        reverse=True
    )
    if not arquivos:
        print("⚠️  Nenhum relatório encontrado na pasta relatorios/")
        relatorio = None
    else:
        relatorio = arquivos[0]
        print(f"  ✅ Relatório: {relatorio}")

    # ── Passo opcional: Enviar email ──────────────────────────────────────────
    if rodar_email:
        passo_atual += 1
        passo(passo_atual, total_passos, "📧 Enviando relatório por email (Outlook)")
        if relatorio:
            try:
                spec     = importlib.util.spec_from_file_location(
                    "email_service",
                    os.path.join(os.path.dirname(__file__), "email_service.py")
                )
                em_mod   = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(em_mod)
                em_mod.enviar(relatorio)
            except Exception as e:
                print(f"❌ Erro no email_service.py: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️  Sem relatório para enviar.")

    # ── Resumo final ──────────────────────────────────────────────────────────
    tempo_total = (time.time() - t_inicio) / 60
    print("\n" + "=" * 55)
    print("  ✅  PIPELINE CONCLUÍDO!")
    print(f"  ⏱️   Tempo total: {tempo_total:.1f} minutos")
    if relatorio:
        print(f"  📄  Relatório:   {relatorio}")
    print("=" * 55)
    print()
    print("  💡 Comandos disponíveis:")
    print("     python main.py              → análise + relatório")
    print("     python main.py --email      → + envia por email")
    print("     python main.py --db         → recarrega banco antes")
    print("     python main.py --db --email → pipeline completo")
    print("=" * 55)


if __name__ == "__main__":
    main()