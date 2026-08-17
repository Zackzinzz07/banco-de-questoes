#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # Contar antes
    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao = %s AND (cargo IS NULL OR cargo = '')", ('sedes_df',))
    antes = cur.fetchone()[0]

    # Preencher cargo para TODAS questões sedes_df sem cargo
    cur.execute("""
        UPDATE questoes
        SET cargo = %s
        WHERE orgao = %s AND (cargo IS NULL OR cargo = '')
    """, ('Técnico de Atendimento Direto ao Cidadão', 'sedes_df'))

    conn.commit()

    # Contar depois
    cur.execute('SELECT COUNT(*) FROM questoes WHERE orgao = %s AND cargo = %s', ('sedes_df', 'Técnico de Atendimento Direto ao Cidadão'))
    depois = cur.fetchone()[0]

    print(f'✅ {cur.rowcount} questões com cargo preenchido!')
    print(f'   Total sedes_df com cargo: {depois}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
