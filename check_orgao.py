#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM questoes WHERE materia IN (%s, %s)', ('Língua Portuguesa', 'Conhecimentos do DF e Legislação'))
    count_materias = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM questoes WHERE materia IN (%s, %s) AND orgao = %s', ('Língua Portuguesa', 'Conhecimentos do DF e Legislação', 'SEDES/DF'))
    count_sedes = cur.fetchone()[0]

    cur.execute('SELECT DISTINCT orgao FROM questoes WHERE materia IN (%s, %s) ORDER BY orgao', ('Língua Portuguesa', 'Conhecimentos do DF e Legislação'))
    orgaos = cur.fetchall()

    print(f'Questões com matérias de SEDES/DF: {count_materias}')
    print(f'  - Com orgao=SEDES/DF: {count_sedes}')
    print(f'  - Sem orgao SEDES/DF: {count_materias - count_sedes}')
    print()
    print('Órgãos encontrados para essas matérias:')
    for (orgao,) in orgaos:
        print(f'  - {orgao}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
