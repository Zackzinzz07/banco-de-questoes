#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    cur.execute("""
        UPDATE questoes
        SET orgao = 'SEDES/DF'
        WHERE materia IN ('Língua Portuguesa', 'Conhecimentos do DF e Legislação')
    """)

    conn.commit()
    print(f'✅ {cur.rowcount} questões atualizadas para SEDES/DF!')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
