#!/usr/bin/env python
import psycopg2
import subprocess
import sys

# Conectar ao banco local
try:
    conn = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
    cur = conn.cursor()

    # Contar questões
    cur.execute('SELECT COUNT(*) FROM questoes')
    total = cur.fetchone()[0]
    print(f"Total de questões no banco local: {total}")

    # Exportar via docker exec
    print("\nExportando para o banco Docker...")

    # Fazer dump do banco local e restaurar no Docker
    subprocess.run([
        'docker', 'exec', '-i', 'training-db-1',
        'psql', '-U', 'postgres', '-d', 'banco_questoes', '-c',
        f'DELETE FROM questoes;'
    ], check=True)

    # Copiar tabela completa
    cur.execute('SELECT * FROM questoes')
    rows = cur.fetchall()

    # Conexão Docker
    docker_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='banco_questoes'
    )
    docker_cur = docker_conn.cursor()

    # Inserir dados
    for row in rows:
        docker_cur.execute('''
            INSERT INTO questoes
            (id, id_qc, enunciado, hash_enunciado, content_hash, alternativas,
             gabarito, comentario, materia, assunto, banca, orgao, cargo, ano,
             prova, fonte, texto_associado, imagens, criada_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', row)

    docker_conn.commit()
    docker_conn.close()

    print(f"✅ {total} questões restauradas no Docker!")

    conn.close()
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)
