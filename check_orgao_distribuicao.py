#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao = %s", ('sedes_df',))
    sedes_df = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao IS NOT NULL AND orgao != %s", ('sedes_df',))
    outros = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao IS NULL OR orgao = ''")
    sem_orgao = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questoes")
    total = cur.fetchone()[0]

    print(f'SEDES/DF: {sedes_df}')
    print(f'Outros: {outros}')
    print(f'Sem órgão: {sem_orgao}')
    print(f'Total: {total}')
    print()
    print(f'Soma: {sedes_df + outros + sem_orgao}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
