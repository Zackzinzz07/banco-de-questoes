#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM questoes')
    total = cur.fetchone()[0]

    cur.execute('SELECT materia, COUNT(*) FROM questoes GROUP BY materia ORDER BY COUNT(*) DESC LIMIT 10')
    results = cur.fetchall()

    print(f'\nTotal de Questões: {total}\n')
    print('Distribuição por Matéria:')
    print('-' * 40)
    for materia, count in results:
        print(f'  {materia}: {count} questões')

    conn.close()
except Exception as e:
    print(f'Erro ao conectar: {e}')
