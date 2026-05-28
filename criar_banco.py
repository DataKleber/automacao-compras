import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres123",
    dbname="postgres"
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('CREATE DATABASE "automacao-compras"')
print("✅ Banco criado com sucesso!")
conn.close()