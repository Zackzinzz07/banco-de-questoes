#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    print('VERIFICANDO SEDES')
    print('=' * 60)

    # SEDES/DF maiúsculas
    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao = %s", ('SEDES/DF',))
    count1 = cur.fetchone()[0]
    print(f'SEDES/DF (maiúsculas): {count1}')

    # sedes_df minúsculas
    cur.execute("SELECT COUNT(*) FROM questoes WHERE orgao = %s", ('sedes_df',))
    count2 = cur.fetchone()[0]
    print(f'sedes_df (minúsculas): {count2}')

    # Outros
    cur.execute("SELECT COUNT(*) FROM questoes WHERE LOWER(orgao) LIKE '%sedes%'")
    total = cur.fetchone()[0]
    print(f'Total com "sedes": {total}')

    print('\n' + '=' * 60)
    print('PCI - Questões coletadas')
    print('=' * 60)

    cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte = %s", ('pci',))
    pci = cur.fetchone()[0]
    print(f'PCI (coletadas): {pci}')

    # Órgãos do PCI
    cur.execute("SELECT orgao, COUNT(*) FROM questoes WHERE fonte = %s GROUP BY orgao LIMIT 5", ('pci',))
    print(f'\nTop órgãos PCI:')
    for orgao, count in cur.fetchall():
        print(f'  {orgao}: {count}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
