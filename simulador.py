"""
simulador.py — Simula dados diários de 20 compradores (como se viesse do SAP/TOTVS)
Automação de Compras | Portfolio: Analista + Engenheiro de Dados
"""

import os
import random
import psycopg2
from datetime import date
from dotenv import load_dotenv

load_dotenv()

COMPRADORES = [
    {"nome": "Ana Lima",         "categoria_foco": "Informática", "volume_medio": 5},
    {"nome": "Bruno Souza",      "categoria_foco": "Telecom",     "volume_medio": 4},
    {"nome": "Carla Mendes",     "categoria_foco": "Mobiliário",  "volume_medio": 6},
    {"nome": "Diego Rocha",      "categoria_foco": "Segurança",   "volume_medio": 3},
    {"nome": "Elisa Castro",     "categoria_foco": "Informática", "volume_medio": 7},
    {"nome": "Felipe Torres",    "categoria_foco": "Escritório",  "volume_medio": 5},
    {"nome": "Gabi Nunes",       "categoria_foco": "Telecom",     "volume_medio": 4},
    {"nome": "Henrique Alves",   "categoria_foco": "Mobiliário",  "volume_medio": 3},
    {"nome": "Isabela Ferreira", "categoria_foco": "Informática", "volume_medio": 6},
    {"nome": "João Pinto",       "categoria_foco": "Segurança",   "volume_medio": 5},
    {"nome": "Karen Dias",       "categoria_foco": "Escritório",  "volume_medio": 4},
    {"nome": "Lucas Martins",    "categoria_foco": "Informática", "volume_medio": 8},
    {"nome": "Marina Gomes",     "categoria_foco": "Telecom",     "volume_medio": 3},
    {"nome": "Nicolas Silva",    "categoria_foco": "Mobiliário",  "volume_medio": 5},
    {"nome": "Olivia Ramos",     "categoria_foco": "Segurança",   "volume_medio": 4},
    {"nome": "Paulo Carvalho",   "categoria_foco": "Informática", "volume_medio": 6},
    {"nome": "Quintina Lopes",   "categoria_foco": "Escritório",  "volume_medio": 3},
    {"nome": "Rafael Costa",     "categoria_foco": "Telecom",     "volume_medio": 5},
    {"nome": "Sara Oliveira",    "categoria_foco": "Mobiliário",  "volume_medio": 4},
    {"nome": "Thiago Barbosa",   "categoria_foco": "Segurança",   "volume_medio": 6},
]

CATEGORIAS = {
    "Informática": {"preco_min": 500,  "preco_max": 15000},
    "Telecom":     {"preco_min": 200,  "preco_max": 8000},
    "Mobiliário":  {"preco_min": 300,  "preco_max": 5000},
    "Segurança":   {"preco_min": 400,  "preco_max": 12000},
    "Escritório":  {"preco_min": 50,   "preco_max": 2000},
    "Limpeza":     {"preco_min": 30,   "preco_max": 500},
    "Manutenção":  {"preco_min": 100,  "preco_max": 3000},
}

FORMAS_PAGAMENTO = ["Boleto", "Cartão Corporativo", "Transferência", "PIX"]
CENTROS_CUSTO    = ["TI", "Administrativo", "Operacional", "RH", "Financeiro"]


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "automacao-compras"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres123"),
    )


def buscar_referencias(conn):
    with conn.cursor() as cur:
        # categoria_principal é o nome real na tabela fornecedores
        cur.execute("SELECT id_fornecedor, nome, categoria_principal FROM fornecedores WHERE ativo = true")
        fornecedores = cur.fetchall()

        cur.execute("SELECT id_produto, nome, categoria, preco_unitario FROM produtos LIMIT 500")
        produtos = cur.fetchall()

    return fornecedores, produtos


def gerar_pedidos_do_dia(fornecedores, produtos, data_ref=None):
    data_ref = data_ref or date.today()
    pedidos_por_comprador = {}

    for comprador in COMPRADORES:
        nome           = comprador["nome"]
        categoria_foco = comprador["categoria_foco"]
        qtd_pedidos    = max(1, comprador["volume_medio"] + random.randint(-2, 3))

        forn_cat = [f for f in fornecedores if f[2] == categoria_foco] or fornecedores
        prod_cat = [p for p in produtos     if p[2] == categoria_foco] or produtos

        pedidos_comprador = []
        for _ in range(qtd_pedidos):
            usa_foco   = random.random() < 0.70
            forn_pool  = forn_cat  if usa_foco else fornecedores
            prod_pool  = prod_cat  if usa_foco else produtos
            cat_usada  = categoria_foco if usa_foco else random.choice(list(CATEGORIAS.keys()))

            forn       = random.choice(forn_pool)
            prod       = random.choice(prod_pool)
            preco_ref  = CATEGORIAS.get(cat_usada, {"preco_min": 100, "preco_max": 5000})
            qtd        = random.randint(1, 20)
            preco_unit = round(random.uniform(preco_ref["preco_min"], preco_ref["preco_max"]), 2)
            total      = round(qtd * preco_unit, 2)

            pedidos_comprador.append({
                "produto":         prod[1],
                "id_produto":      prod[0],
                "categoria":       cat_usada,
                "fornecedor":      forn[1],
                "id_fornecedor":   forn[0],
                "quantidade":      qtd,
                "valor_unitario":  preco_unit,
                "valor_total":     total,
                "data_compra":     data_ref,
                "ano":             data_ref.year,
                "mes":             data_ref.month,
                "trimestre":       (data_ref.month - 1) // 3 + 1,
                "centro_custo":    random.choice(CENTROS_CUSTO),
                "status_pedido":   random.choices(
                                       ["pendente", "aprovado", "entregue"],
                                       weights=[0.3, 0.5, 0.2]
                                   )[0],
                "forma_pagamento": random.choice(FORMAS_PAGAMENTO),
                "prazo_pagamento": random.choice([15, 28, 30, 45, 60]),
                "nf_numero":       f"NF{random.randint(100000, 999999)}",
            })

        pedidos_por_comprador[nome] = pedidos_comprador

    return pedidos_por_comprador


def inserir_pedidos(conn, todos_pedidos):
    sql = """
        INSERT INTO compras
            (produto, id_produto, categoria, fornecedor, id_fornecedor,
             quantidade, valor_unitario, valor_total, data_compra,
             ano, mes, trimestre, centro_custo, status_pedido,
             forma_pagamento, prazo_pagamento, nf_numero)
        VALUES
            (%(produto)s, %(id_produto)s, %(categoria)s, %(fornecedor)s, %(id_fornecedor)s,
             %(quantidade)s, %(valor_unitario)s, %(valor_total)s, %(data_compra)s,
             %(ano)s, %(mes)s, %(trimestre)s, %(centro_custo)s, %(status_pedido)s,
             %(forma_pagamento)s, %(prazo_pagamento)s, %(nf_numero)s)
    """
    with conn.cursor() as cur:
        cur.executemany(sql, todos_pedidos)
    conn.commit()


def simular_dia(data_ref=None):
    data_ref = data_ref or date.today()
    print(f"\n{'='*55}")
    print(f"  🏭  SIMULADOR ERP — {data_ref.strftime('%d/%m/%Y')}")
    print(f"{'='*55}")

    conn = conectar()
    print("🔌 Conexão com PostgreSQL estabelecida!")

    fornecedores, produtos = buscar_referencias(conn)
    print(f"📋 Referências: {len(fornecedores)} fornecedores ativos | {len(produtos)} produtos")

    pedidos_por_comprador = gerar_pedidos_do_dia(fornecedores, produtos, data_ref)

    print(f"\n📦 Pedidos gerados pelos 20 compradores:")
    todos_pedidos = []
    for nome, pedidos in pedidos_por_comprador.items():
        val = sum(p["valor_total"] for p in pedidos)
        print(f"   {nome:<22}  {len(pedidos):>3} pedidos  |  R$ {val:>12,.2f}")
        todos_pedidos.extend(pedidos)

    total_val = sum(p["valor_total"] for p in todos_pedidos)
    print(f"\n💰 Total do dia: R$ {total_val:,.2f}  ({len(todos_pedidos)} pedidos)")

    inserir_pedidos(conn, todos_pedidos)
    print(f"✅ {len(todos_pedidos)} pedidos inseridos no banco!")

    conn.close()
    print(f"🚀 Simulação de {data_ref.strftime('%d/%m/%Y')} concluída!")
    return len(todos_pedidos), total_val


if __name__ == "__main__":
    simular_dia()