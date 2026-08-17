#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # Normalizar SEDES/DF → sedes_df
    cur.execute('UPDATE questoes SET orgao = %s WHERE orgao = %s', ('sedes_df', 'SEDES/DF'))

    conn.commit()
    print(f'✅ {cur.rowcount} questões normalizadas (SEDES/DF → sedes_df)!')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
