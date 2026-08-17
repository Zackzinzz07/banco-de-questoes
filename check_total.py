#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM questoes')
    total = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM questoes WHERE orgao = %s', ('SEDES/DF',))
    sedes = cur.fetchone()[0]

    print(f'Total: {total}')
    print(f'SEDES/DF: {sedes}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
