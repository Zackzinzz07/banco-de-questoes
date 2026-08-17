#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    print('VERIFICANDO QUALIDADE DOS DADOS')
    print('=' * 60)

    # Total
    cur.execute('SELECT COUNT(*) FROM questoes')
    total = cur.fetchone()[0]
    print(f'\nTotal de questões: {total}')

    # Com matéria
    cur.execute("SELECT COUNT(*) FROM questoes WHERE materia IS NOT NULL AND materia != ''")
    com_materia = cur.fetchone()[0]
    print(f'Com matéria: {com_materia}')

    # Com enunciado
    cur.execute("SELECT COUNT(*) FROM questoes WHERE enunciado IS NOT NULL AND enunciado != ''")
    com_enunciado = cur.fetchone()[0]
    print(f'Com enunciado: {com_enunciado}')

    # Com alternativas
    cur.execute("SELECT COUNT(*) FROM questoes WHERE alternativas IS NOT NULL AND alternativas != ''")
    com_alt = cur.fetchone()[0]
    print(f'Com alternativas: {com_alt}')

    print('\n' + '=' * 60)
    print('EXEMPLO DE QUESTÃO:')
    print('=' * 60)

    cur.execute("""
        SELECT id, materia, orgao, cargo, enunciado, alternativas
        FROM questoes
        WHERE enunciado IS NOT NULL
        LIMIT 1
    """)
    row = cur.fetchone()

    if row:
        print(f"\nID: {row[0]}")
        print(f"Matéria: {row[1]}")
        print(f"Órgão: {row[2]}")
        print(f"Cargo: {row[3]}")
        print(f"Enunciado: {row[4][:100]}...")
        print(f"Alternativas: {row[5][:100]}...")

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
