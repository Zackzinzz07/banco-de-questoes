#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # 1. Normalizar SEDES/DF → sedes_df
    cur.execute("UPDATE questoes SET orgao = %s WHERE LOWER(orgao) = %s", ('sedes_df', 'sedes/df'))
    conn.commit()
    print(f'✅ Normalizados: {cur.rowcount}')

    # 2. Preencher cargo para TODAS sedes_df sem cargo
    cur.execute("""
        UPDATE questoes
        SET cargo = %s
        WHERE orgao = %s AND (cargo IS NULL OR cargo = '')
    """, ('Técnico de Atendimento Direto ao Cidadão', 'sedes_df'))

    conn.commit()
    print(f'✅ Cargo preenchido: {cur.rowcount}')

    # 3. Verificar
    cur.execute('SELECT COUNT(*) FROM questoes WHERE orgao = %s AND cargo = %s', ('sedes_df', 'Técnico de Atendimento Direto ao Cidadão'))
    total = cur.fetchone()[0]
    print(f'✅ Total SEDES/DF com cargo: {total}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
