#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute('SELECT orgao, COUNT(*) as cnt FROM questoes GROUP BY orgao ORDER BY cnt DESC LIMIT 5')
    results = cur.fetchall()

    print('Top órgãos coletados:')
    for orgao, count in results:
        print(f'  {orgao}: {count}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
