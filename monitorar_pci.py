"""Monitor live do PCI re-coleta com categoria/tema."""

import psycopg2
import time
import sys

def status():
    con = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = con.cursor()

    # Total PCI
    cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci'")
    total_pci = cur.fetchone()[0]

    # Com categoria
    cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci' AND categoria IS NOT NULL")
    com_cat = cur.fetchone()[0]

    # Com tema
    cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci' AND tema IS NOT NULL")
    com_tema = cur.fetchone()[0]

    # Progresso (últimas categorias)
    cur.execute("""
        SELECT chave, ultima_pagina
        FROM progresso_scraper
        WHERE fonte='pci'
        ORDER BY ultima_pagina DESC
        LIMIT 3
    """)
    progresso = cur.fetchall()

    # Exemplo de questão
    cur.execute("""
        SELECT materia, categoria, tema, enunciado
        FROM questoes
        WHERE fonte='pci' AND categoria IS NOT NULL
        LIMIT 1
    """)
    exemplo = cur.fetchone()

    print("\n" + "="*70)
    print("PCI RE-COLETA - STATUS LIVE")
    print("="*70)
    print(f"\nTotal PCI: {total_pci:,}")
    print(f"  Com categoria: {com_cat:,} ({100*com_cat/max(1,total_pci):.1f}%)")
    print(f"  Com tema: {com_tema:,} ({100*com_tema/max(1,total_pci):.1f}%)")

    if progresso:
        print(f"\nProgresso (últimas categorias):")
        for chave, pag in progresso:
            print(f"  {chave[:50]:50} página {pag}")

    if exemplo:
        print(f"\nExemplo de questão com categoria:")
        print(f"  Matéria: {exemplo[0]}")
        print(f"  Categoria: {exemplo[1]}")
        print(f"  Tema: {exemplo[2]}")
        print(f"  Enunciado: {exemplo[3][:60]}...")

    con.close()

    return total_pci, com_cat

if __name__ == "__main__":
    print("\n[MONITOR] PCI Live (CTRL+C para parar)\n")

    try:
        while True:
            total, com_cat = status()

            if com_cat > 0 and total > 100:
                print("\n✓ CATEGORIA SENDO SALVO CORRETAMENTE!")
                break

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n[FIM]")
