#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute('SELECT DISTINCT materia, COUNT(*) FROM questoes GROUP BY materia ORDER BY COUNT(*) DESC LIMIT 15')
    results = cur.fetchall()

    print('Matérias no banco:')
    for materia, count in results:
        print(f'  {materia}: {count}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
