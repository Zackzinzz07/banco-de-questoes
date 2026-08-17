#!/usr/bin/env python
import psycopg2

conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
cur = conn.cursor()

print('\n' + '=' * 80)
print('📊 RELATÓRIO DE COLETA - DISPONIBILIDADE vs COLETADO')
print('=' * 80)

# Total geral
cur.execute('SELECT COUNT(*) FROM questoes')
total = cur.fetchone()[0]
print(f'\nTotal no banco: {total:,} questões\n')

# Por matéria
cur.execute("""
    SELECT materia, COUNT(*) as qtd
    FROM questoes
    GROUP BY materia
    ORDER BY qtd DESC
""")
print('🎓 POR MATÉRIA:')
print('-' * 80)
materias = cur.fetchall()
for materia, qtd in materias:
    print(f'  {materia:40} {qtd:5,}')

# Por órgão
cur.execute("""
    SELECT orgao, COUNT(*) as qtd
    FROM questoes
    GROUP BY orgao
    ORDER BY qtd DESC
""")
print('\n🏛️ POR ÓRGÃO:')
print('-' * 80)
for orgao, qtd in cur.fetchall():
    print(f'  {orgao:40} {qtd:5,}')

# Por fonte
cur.execute("""
    SELECT fonte, COUNT(*) as qtd
    FROM questoes
    GROUP BY fonte
    ORDER BY qtd DESC
""")
print('\n📡 POR FONTE:')
print('-' * 80)
for fonte, qtd in cur.fetchall():
    print(f'  {fonte:40} {qtd:5,}')

print('\n' + '=' * 80)
print(f'✅ STATUS: {total:,} questões prontas para gerar simulados')
print('=' * 80 + '\n')

conn.close()
