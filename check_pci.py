#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # PCI
    cur.execute('SELECT COUNT(*) FROM questoes WHERE fonte = %s', ('pci',))
    pci_total = cur.fetchone()[0]

    # QConcursos
    cur.execute('SELECT COUNT(*) FROM questoes WHERE fonte = %s', ('qconcursos',))
    qc_total = cur.fetchone()[0]

    # Total
    cur.execute('SELECT COUNT(*) FROM questoes')
    total = cur.fetchone()[0]

    print(f'PCI: {pci_total}')
    print(f'QConcursos: {qc_total}')
    print(f'Total: {total}')
    print()

    # PCI top órgãos
    print('PCI - Top órgãos:')
    cur.execute('SELECT orgao, COUNT(*) FROM questoes WHERE fonte = %s GROUP BY orgao ORDER BY COUNT(*) DESC LIMIT 5', ('pci',))
    for orgao, count in cur.fetchall():
        print(f'  {orgao}: {count}')

    conn.close()
except Exception as e:
    print(f'Erro: {e}')
