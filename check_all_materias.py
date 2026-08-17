#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # Todas as matérias
    cur.execute('SELECT materia, COUNT(*) FROM questoes GROUP BY materia ORDER BY COUNT(*) DESC')
    results = cur.fetchall()

    print('TODAS AS MATÉRIAS:')
    print()
    total = 0
    for materia, count in results:
        print(f'{materia}: {count}')
        total += count

    print()
    print(f'Total: {total}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
