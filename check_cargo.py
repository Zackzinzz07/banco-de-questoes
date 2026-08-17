#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questoes WHERE cargo IS NOT NULL AND cargo != ''")
    com_cargo = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questoes WHERE cargo IS NULL OR cargo = ''")
    sem_cargo = cur.fetchone()[0]

    print(f'Com cargo: {com_cargo}')
    print(f'Sem cargo: {sem_cargo}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
