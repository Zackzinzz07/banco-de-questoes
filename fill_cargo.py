#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # Preencher cargo para SEDES/DF
    cur.execute("""
        UPDATE questoes
        SET cargo = %s
        WHERE orgao = %s AND (cargo IS NULL OR cargo = '')
    """, ('Técnico de Atendimento Direto ao Cidadão', 'sedes_df'))

    conn.commit()
    print(f'✅ {cur.rowcount} questões com cargo preenchido!')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
