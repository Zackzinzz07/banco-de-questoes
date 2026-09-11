import pytest

import db


def questao_exemplo(**extras):
    q = {
        "id_qc": "Q1234567",
        "enunciado": "Qual é a capital do Brasil?",
        "alternativas": {"A": "Brasília", "B": "Goiânia", "C": "Rio", "D": "SP", "E": "BH"},
        "gabarito": "A",
        "comentario": None,
        "materia": "Língua Portuguesa",
        "assunto": "Interpretação de textos",
        "banca": "Instituto Quadrix",
        "orgao": "SEDES/DF",
        "ano": 2026,
        "prova": "Técnico Administrativo",
        "fonte": "qconcursos",
    }
    q.update(extras)
    return q


def test_salvar_e_ler():
    con = db.conectar()
    assert db.salvar_questao(con, questao_exemplo()) is True
    linha = con.execute("SELECT * FROM questoes").fetchone()
    assert linha["id_qc"] == "Q1234567"
    assert linha["materia"] == "Língua Portuguesa"
    assert linha["usada_em_simulado"] == 0


def test_dedupe_por_id_qc():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    assert db.salvar_questao(con, questao_exemplo(enunciado="Outro texto")) is False


def test_dedupe_por_hash_enunciado():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    repetida = questao_exemplo(id_qc=None, enunciado="  qual  é a CAPITAL do Brasil? ")
    assert db.salvar_questao(con, repetida) is False


def test_duas_questoes_sem_id_qc_nao_conflitam():
    con = db.conectar()
    assert db.salvar_questao(con, questao_exemplo(id_qc=None)) is True
    assert db.salvar_questao(con, questao_exemplo(id_qc=None, enunciado="Texto diferente.")) is True


def test_normalizar_enunciado():
    assert db.normalizar_enunciado("  Olá   MUNDO \n ") == "olá mundo"


def test_fonte_invalida_raises_error():
    con = db.conectar()
    with pytest.raises(ValueError, match="fonte inválida"):
        db.salvar_questao(con, questao_exemplo(fonte="outra"))


def test_sorteio_sem_repeticao():
    con = db.conectar()
    for i in range(5):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    sorteadas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    assert len(sorteadas) == 3
    assert isinstance(sorteadas[0]["alternativas"], dict)
    db.marcar_usadas(con, [q["id"] for q in sorteadas])
    restantes = db.sortear_questoes(con, "Língua Portuguesa", 2)
    ids_novos = {q["id"] for q in restantes}
    assert ids_novos.isdisjoint({q["id"] for q in sorteadas})


def test_sorteio_completa_com_repetidas(capsys):
    con = db.conectar()
    for i in range(3):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    todas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    db.marcar_usadas(con, [q["id"] for q in todas])
    de_novo = db.sortear_questoes(con, "Língua Portuguesa", 2)
    assert len(de_novo) == 2
    assert "repetidas" in capsys.readouterr().out


def test_zerar_usadas():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    q = db.sortear_questoes(con, "Língua Portuguesa", 1)
    db.marcar_usadas(con, [q[0]["id"]])
    db.zerar_usadas(con)
    assert (
        con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"]
        == 0
    )


def test_progresso():
    con = db.conectar()
    assert db.obter_progresso(con, "qconcursos", "Direito Administrativo") == 0
    db.salvar_progresso(con, "qconcursos", "Direito Administrativo", 7)
    db.salvar_progresso(con, "qconcursos", "Direito Administrativo", 8)
    assert db.obter_progresso(con, "qconcursos", "Direito Administrativo") == 8


def test_salva_e_le_texto_associado():
    con = db.conectar()
    q = questao_exemplo(texto_associado="Poema base da questão.", imagens=["https://x/a.png"])
    db.salvar_questao(con, q)
    lida = db.sortear_questoes(con, "Língua Portuguesa", 1)[0]
    assert lida["texto_associado"] == "Poema base da questão."
    assert lida["imagens"] == ["https://x/a.png"]


def test_completar_texto_associado_preenche_so_quando_vazio():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QT1"))
    assert db.completar_texto_associado(con, "QT1", "Texto novo.", ["u1"]) is True
    assert db.completar_texto_associado(con, "QT1", "Outro texto.", []) is False
    linha = con.execute("SELECT texto_associado FROM questoes WHERE id_qc='QT1'").fetchone()
    assert linha["texto_associado"] == "Texto novo."


def test_sem_gabarito_e_atualizar():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="Q1", gabarito=None, enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="Q2", gabarito="B", enunciado="Dois?"))
    db.salvar_questao(con, questao_exemplo(id_qc=None, gabarito=None, enunciado="Três?"))
    pendentes = db.sem_gabarito(con)
    assert [p["id_qc"] for p in pendentes] == ["Q1"]
    db.atualizar_gabarito(con, "Q1", "C", "Comentário do professor.")
    linha = con.execute("SELECT gabarito, comentario FROM questoes WHERE id_qc='Q1'").fetchone()
    assert (linha["gabarito"], linha["comentario"]) == ("C", "Comentário do professor.")


def test_estatisticas():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QA", enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="QB", enunciado="Dois?", gabarito=None))
    db.salvar_questao(con, questao_exemplo(id_qc="QC1", enunciado="Três?", materia="SUAS"))
    usada = db.sortear_questoes(con, "SUAS", 1)
    db.marcar_usadas(con, [usada[0]["id"]])
    est = db.estatisticas(con)
    assert est["Língua Portuguesa"] == {"total": 2, "ineditas": 2, "usadas": 0, "sem_gabarito": 1}
    assert est["SUAS"] == {"total": 1, "ineditas": 0, "usadas": 1, "sem_gabarito": 0}


def test_salvar_questao_com_cargo():
    """Test saving question with cargo field."""
    con = db.conectar()
    q = questao_exemplo(
        id_qc="QCARGO1", enunciado="Teste com cargo", cargo="Policial Rodoviário Federal"
    )
    resultado = db.salvar_questao(con, q)
    assert resultado is True

    # Verify cargo was saved
    linhas = con.execute(
        "SELECT cargo FROM questoes WHERE enunciado=%s", ("Teste com cargo",)
    ).fetchall()
    assert len(linhas) == 1
    assert linhas[0]["cargo"] == "Policial Rodoviário Federal"


def test_sortear_questoes_com_cargo():
    """Test cargo filtering in sortear_questoes."""
    con = db.conectar()
    # Insert two questions with different cargos
    q1 = questao_exemplo(
        id_qc="QPRF1",
        enunciado="Q1 PRF",
        materia="Direito Constitucional",
        cargo="Policial Rodoviário Federal",
        orgao="PRF",
        banca="Cebraspe",
    )
    q2 = questao_exemplo(
        id_qc="QBACEN1",
        enunciado="Q2 BACEN",
        materia="Direito Constitucional",
        cargo="Técnico",
        orgao="Banco Central",
        banca="Cebraspe",
    )
    db.salvar_questao(con, q1)
    db.salvar_questao(con, q2)

    # Filter by cargo
    resultados = db.sortear_questoes(
        con, "Direito Constitucional", 1, cargo="Policial Rodoviário Federal"
    )
    assert len(resultados) == 1
    assert "PRF" in resultados[0]["enunciado"]


def test_sortear_questoes_sem_cargo_filter():
    """Test that sorting still works without cargo filter (backward compat)."""
    con = db.conectar()
    q = questao_exemplo(id_qc="QSEMCARGO", enunciado="Q sem cargo", materia="Português")
    db.salvar_questao(con, q)

    # Should work without cargo parameter
    resultados = db.sortear_questoes(con, "Português", 1)
    assert len(resultados) >= 1
    assert resultados[0]["enunciado"] == "Q sem cargo"


def test_sortear_questoes_com_multiplos_filtros():
    """Test combining cargo + banca + orgao filters."""
    con = db.conectar()
    q = questao_exemplo(
        id_qc="QMULTIFILTRO",
        enunciado="Q filtros múltiplos",
        materia="Matemática",
        cargo="Técnico",
        orgao="BACEN",
        banca="Cebraspe",
    )
    db.salvar_questao(con, q)

    # Combined filter
    resultados = db.sortear_questoes(
        con, "Matemática", 1, banca="Cebraspe", orgao="BACEN", cargo="Técnico"
    )
    assert len(resultados) >= 1
    assert "filtros múltiplos" in resultados[0]["enunciado"]


def test_salvar_questao_normaliza_gabarito_vazio_para_null():
    """Gabarito '' (string vazia) é 'sem gabarito', não um gabarito válido.
    O SQLite legado trazia 367 questões assim; guardá-las como '' as torna
    invisíveis para a fase de coleta de gabaritos."""
    con = db.conectar()
    db.salvar_questao(
        con, questao_exemplo(id_qc="QVAZIO1", enunciado="Gabarito vazio?", gabarito="")
    )
    linha = con.execute("SELECT gabarito FROM questoes WHERE id_qc='QVAZIO1'").fetchone()
    assert linha["gabarito"] is None
    con.close()


def test_sem_gabarito_encontra_gabarito_string_vazia():
    """'WHERE gabarito IS NULL' sozinho não acha as questões com ''."""
    con = db.conectar()
    con.execute(
        "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, content_hash,"
        " alternativas, gabarito, materia, fonte)"
        " VALUES ('QVAZIO2','Enunciado vazio?','h_vazio2','c_vazio2','{}','',"
        " 'SUAS','qconcursos')"
    )
    pendentes = db.sem_gabarito(con)
    assert "QVAZIO2" in [p["id_qc"] for p in pendentes]
    con.close()


def test_estatisticas_conta_gabarito_vazio_como_sem_gabarito():
    con = db.conectar()
    con.execute(
        "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, content_hash,"
        " alternativas, gabarito, materia, fonte)"
        " VALUES ('QVAZIO3','Outro vazio?','h_vazio3','c_vazio3','{}','',"
        " 'SUAS','qconcursos')"
    )
    assert db.estatisticas(con)["SUAS"]["sem_gabarito"] == 1
    con.close()


def test_salvar_questao_persiste_banca_e_orgao():
    """banca/orgao são usados como filtro em sortear_questoes mas nenhum
    teste checava a coluna direto — cobrindo o mesmo bug do cargo."""
    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QBANCAORGAO1",
            enunciado="Teste banca e orgao",
            banca="Cebraspe",
            orgao="PRF",
        ),
    )
    linha = con.execute(
        "SELECT banca, orgao FROM questoes WHERE enunciado=%s",
        ("Teste banca e orgao",),
    ).fetchone()
    assert linha["banca"] == "Cebraspe"
    assert linha["orgao"] == "PRF"
    con.close()


def test_conectar_liga_autocommit_para_nao_prender_transacao_aberta():
    """Sem autocommit, um SELECT sozinho deixa a conexão 'idle in transaction'
    até alguém commitar/fechar — isso é o que trava a suíte inteira quando
    vários testes abrem conexão e não fecham."""
    import psycopg2.extensions as ext

    con = db.conectar()
    con.execute("SELECT 1")
    assert con._con.get_transaction_status() == ext.TRANSACTION_STATUS_IDLE
    con.close()


def test_migracoes_rodam_uma_unica_vez_por_processo(monkeypatch):
    """ALTER TABLE (dentro das migrations) pede AccessExclusiveLock mesmo com
    IF NOT EXISTS. Rodar isso em toda chamada de conectar() é o que causa a
    fila de locks quando o processo tem várias conexões vivas ao mesmo tempo."""
    import migrations.migration_002 as m2

    chamadas = []
    monkeypatch.setattr(m2, "aplicar", lambda con: chamadas.append(1))
    monkeypatch.setattr(db, "_MIGRACOES_APLICADAS", False)

    con1 = db.conectar()
    con2 = db.conectar()

    assert len(chamadas) == 1
    con1.close()
    con2.close()


def test_sortear_questoes_cargo_nao_encontra_quando_diferente():
    """Test that filtering by different cargo returns no results."""
    con = db.conectar()
    q = questao_exemplo(
        id_qc="QCARGO2",
        enunciado="Q com cargo PRF",
        materia="Direito",
        cargo="Policial Rodoviário Federal",
        orgao="PRF",
    )
    db.salvar_questao(con, q)

    # Filter by different cargo - should return empty
    resultados = db.sortear_questoes(con, "Direito", 1, cargo="Técnico Administrativo")
    assert len(resultados) == 0


def test_salvar_questao_com_byte_nul_no_enunciado_nao_quebra():
    """PostgreSQL rejeita 0x00 em text. Uma questão do PCI com esse byte
    derrubou a categoria `matematica` inteira; a gravação tem que limpar o
    caractere em vez de estourar."""
    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QNUL1",
            enunciado="Quanto é 2\x00 + 2?",
            alternativas={"A": "4\x00", "B": "5"},
        ),
    )
    linha = con.execute(
        "SELECT enunciado, alternativas FROM questoes WHERE id_qc=%s", ("QNUL1",)
    ).fetchone()
    assert linha is not None, "a questão não foi gravada"
    assert "\x00" not in linha["enunciado"]
    assert linha["enunciado"] == "Quanto é 2 + 2?"
    assert "\x00" not in str(linha["alternativas"])
    con.close()


def test_migration_003_adiciona_coluna_formato_com_default():
    """Cobre a migration em si, não a inferência de db.salvar_questao: insert
    cru, sem passar por formato nenhum, tem que cair no default da coluna."""
    con = db.conectar()
    con.execute(
        "INSERT INTO questoes (enunciado, hash_enunciado, content_hash, alternativas,"
        " materia, fonte) VALUES ('Q formato default?', 'h_fmt_default', 'c_fmt_default',"
        " '{}', 'Direito Administrativo', 'pci')"
    )
    linha = con.execute(
        "SELECT formato FROM questoes WHERE hash_enunciado='h_fmt_default'"
    ).fetchone()
    assert linha["formato"] == "multipla_escolha"
    con.close()


def test_salvar_questao_infere_formato_multipla_escolha_com_alternativas_a_e():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QFMT1", enunciado="Múltipla escolha?"))
    linha = con.execute("SELECT formato FROM questoes WHERE id_qc='QFMT1'").fetchone()
    assert linha["formato"] == "multipla_escolha"


def test_salvar_questao_infere_formato_certo_errado_sem_alternativa_d():
    con = db.conectar()
    q = questao_exemplo(
        id_qc="QFMT2",
        enunciado="Certo ou errado?",
        alternativas={"C": "Certo", "E": "Errado"},
        gabarito="C",
    )
    db.salvar_questao(con, q)
    linha = con.execute("SELECT formato FROM questoes WHERE id_qc='QFMT2'").fetchone()
    assert linha["formato"] == "certo_errado"


def test_salvar_questao_respeita_formato_explicito():
    """formato informado vence a inferência — cobre reimportação/correção manual."""
    con = db.conectar()
    q = questao_exemplo(id_qc="QFMT3", enunciado="Formato explícito?", formato="certo_errado")
    db.salvar_questao(con, q)
    linha = con.execute("SELECT formato FROM questoes WHERE id_qc='QFMT3'").fetchone()
    assert linha["formato"] == "certo_errado"


def test_sortear_questoes_filtra_por_formato():
    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QFMTME",
            enunciado="Questão múltipla escolha de Direito",
            materia="Direito Constitucional",
        ),
    )
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QFMTCE",
            enunciado="Questão certo errado de Direito",
            materia="Direito Constitucional",
            alternativas={"C": "Certo", "E": "Errado"},
            gabarito="E",
        ),
    )

    so_ce = db.sortear_questoes(con, "Direito Constitucional", 5, formato="certo_errado")
    assert [q["id_qc"] for q in so_ce] == ["QFMTCE"]

    so_me = db.sortear_questoes(con, "Direito Constitucional", 5, formato="multipla_escolha")
    assert [q["id_qc"] for q in so_me] == ["QFMTME"]


def test_sortear_questoes_sem_formato_devolve_os_dois_tipos():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QFMTAMBOS1", enunciado="Uma", materia="Ética"))
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QFMTAMBOS2",
            enunciado="Outra",
            materia="Ética",
            alternativas={"C": "Certo", "E": "Errado"},
            gabarito="C",
        ),
    )
    resultado = db.sortear_questoes(con, "Ética", 5)
    assert {q["id_qc"] for q in resultado} == {"QFMTAMBOS1", "QFMTAMBOS2"}


def test_sortear_questoes_nao_devolve_sempre_as_mesmas():
    """O RANDOM() do sorteio era código morto.

    `SELECT DISTINCT ON (content_hash) ... ORDER BY content_hash, ..., RANDOM()`
    obriga o ORDER BY a começar pelo content_hash, então o LIMIT pegava as N
    primeiras em ordem de hash e o RANDOM() só desempataria linhas de mesmo
    hash — que, por definição do DISTINCT ON, nunca existem. Resultado: o mesmo
    simulado toda vez, e sem relação nenhuma com equilíbrio de conteúdo.
    """
    con = db.conectar()
    for n in range(60):
        db.salvar_questao(
            con,
            questao_exemplo(
                id_qc=f"QSORT{n}",
                enunciado=f"Enunciado sorteável número {n}?",
                materia="Direito Administrativo",
            ),
        )

    sorteios = {
        tuple(q["id"] for q in db.sortear_questoes(con, "Direito Administrativo", 10))
        for _ in range(3)
    }
    con.close()

    assert len(sorteios) > 1, "três sorteios seguidos devolveram exatamente as mesmas questões"


def test_migration_004_cria_tabelas_materias_e_conteudos():
    """A migration roda no conectar() -- as tabelas já existem sem precisar
    chamar nada explicitamente."""
    con = db.conectar()
    materias_cols = {
        r["column_name"]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='materias'"
        ).fetchall()
    }
    conteudos_cols = {
        r["column_name"]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='conteudos'"
        ).fetchall()
    }
    assert {"id", "nome"} <= materias_cols
    assert {"id", "materia_id", "nome"} <= conteudos_cols

    questoes_cols = {
        r["column_name"]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='questoes'"
        ).fetchall()
    }
    assert "conteudo_id" in questoes_cols


def test_migration_004_agrupa_variantes_de_materia_e_faz_backfill():
    """'Informática' e 'Noções de Informática' são a mesma matéria pro
    taxonomia -- tem que virar UMA linha em `materias`, não duas, e cada
    questão tem que apontar pro conteúdo certo via `categoria`."""
    import migrations.migration_004 as m4

    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QINF1",
            enunciado="Questão de Informática 1?",
            materia="Informática",
            categoria="Hardware",
        ),
    )
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QINF2",
            enunciado="Questão de Informática 2?",
            materia="Informática",
            categoria="Hardware",
        ),
    )
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QINF3",
            enunciado="Questão de Noções de Informática?",
            materia="Noções de Informática",
            categoria="Redes",
        ),
    )

    # A migration já rodou em conectar() antes destas questões existirem;
    # chamar de novo é o mecanismo de idempotência que pega dado novo.
    assert m4.aplicar(con) is True

    materias = con.execute(
        "SELECT id, nome FROM materias WHERE nome IN ('Informática', 'Noções de Informática')"
    ).fetchall()
    assert len(materias) == 1, "duas variantes da mesma matéria viraram duas linhas"
    assert materias[0]["nome"] == "Informática"  # variante com mais questões (2 x 1)
    materia_id = materias[0]["id"]

    conteudos = con.execute(
        "SELECT nome FROM conteudos WHERE materia_id=%s ORDER BY nome", (materia_id,)
    ).fetchall()
    assert [c["nome"] for c in conteudos] == ["Hardware", "Redes"]

    linhas = con.execute(
        "SELECT q.id_qc, c.nome FROM questoes q JOIN conteudos c ON c.id = q.conteudo_id"
        " WHERE q.id_qc IN ('QINF1', 'QINF2', 'QINF3') ORDER BY q.id_qc"
    ).fetchall()
    assert [(r["id_qc"], r["nome"]) for r in linhas] == [
        ("QINF1", "Hardware"),
        ("QINF2", "Hardware"),
        ("QINF3", "Redes"),
    ]


def test_migration_004_e_idempotente():
    """Rodar duas vezes não duplica materias nem conteudos."""
    import migrations.migration_004 as m4

    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QIDEMP",
            enunciado="Questão idempotência?",
            materia="Atualidades",
            categoria="Geopolítica",
        ),
    )

    assert m4.aplicar(con) is True
    assert m4.aplicar(con) is True

    total = con.execute(
        "SELECT COUNT(*) c FROM conteudos WHERE nome='Geopolítica'"
    ).fetchone()["c"]
    assert total == 1


def test_migration_004_nao_sobrescreve_conteudo_id_ja_preenchido():
    """O backfill só toca `conteudo_id IS NULL` -- não pisa em quem já foi
    resolvido por outro caminho (ex.: mapear_conteudo_edital.py no futuro)."""
    import migrations.migration_004 as m4

    con = db.conectar()
    db.salvar_questao(
        con,
        questao_exemplo(
            id_qc="QPRESET",
            enunciado="Questão com conteudo_id manual?",
            materia="Atualidades",
            categoria="Geopolítica",
        ),
    )
    assert m4.aplicar(con) is True

    conteudo_id_original = con.execute(
        "SELECT conteudo_id FROM questoes WHERE id_qc='QPRESET'"
    ).fetchone()["conteudo_id"]
    assert conteudo_id_original is not None

    cur = con.execute(
        "INSERT INTO conteudos (materia_id, nome)"
        " SELECT materia_id, 'Outro Assunto Qualquer' FROM conteudos"
        " WHERE id=%s"
        " ON CONFLICT (materia_id, nome) DO UPDATE SET nome = EXCLUDED.nome"
        " RETURNING id",
        (conteudo_id_original,),
    )
    outro_conteudo = cur.fetchone()["id"]
    con.execute(
        "UPDATE questoes SET conteudo_id=%s WHERE id_qc='QPRESET'", (outro_conteudo,)
    )
    con.commit()

    assert m4.aplicar(con) is True

    conteudo_id_final = con.execute(
        "SELECT conteudo_id FROM questoes WHERE id_qc='QPRESET'"
    ).fetchone()["conteudo_id"]
    assert conteudo_id_final == outro_conteudo
