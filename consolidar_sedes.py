#!/usr/bin/env python
import psycopg2

conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
cur = conn.cursor()

# Consolidar SEDES/DF → sedes_df
cur.execute("UPDATE questoes SET orgao = %s WHERE orgao = %s", ('sedes_df', 'SEDES/DF'))
conn.commit()

# Verificar total
cur.execute('SELECT COUNT(*) FROM questoes WHERE orgao = %s', ('sedes_df',))
total_sedes = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM questoes')
total_geral = cur.fetchone()[0]

print(f'✅ Consolidados: {cur.rowcount}')
print(f'Total SEDES: {total_sedes}')
print(f'Total Geral: {total_geral}')

conn.close()
