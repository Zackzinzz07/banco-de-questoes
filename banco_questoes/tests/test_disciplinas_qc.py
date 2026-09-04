"""Testes do registro de disciplinas do QConcursos.

O coletor iterava as 8 matérias do `edital.py` (SEDES/DF), então nenhum dos
outros 8 concursos configurados em `configuracoes_editais/` conseguia coletar
uma questão sequer. Este registro desacopla a coleta do edital: o QC passa a
ser varrido por disciplina, e os editais só escolhem o que usar.

Os IDs foram confirmados na interface logada do QConcursos em 03/09/2026.
"""

from scrapers.qc import disciplinas


def test_traz_as_disciplinas_ja_usadas_pelo_sedes():
    """Os nomes das 8 originais NÃO podem mudar: são a chave do progresso
    salvo em `progresso_scraper` e o valor de `materia` das 10.240 questões
    do QC já gravadas. Renomear rachava os dados em dois."""
    for nome in (
        "Língua Portuguesa",
        "Conhecimentos do DF e Legislação",
        "SUAS",
        "Direito Constitucional",
        "Direito Administrativo",
        "Atendimento, Rotinas Administrativas e Arquivologia",
        "Recursos Materiais, Patrimônio e Compras",
        "Programas e Benefícios do DF",
    ):
        assert nome in disciplinas.DISCIPLINAS, f"{nome} sumiu do registro"


def test_ids_das_originais_batem_com_os_do_edital():
    import edital

    for nome, ids in disciplinas.DISCIPLINAS.items():
        if nome not in edital.MATERIAS:
            continue
        url_antiga = edital.MATERIAS[nome].get("url_qc") or ""
        for identificador in ids:
            assert f"discipline_ids%5B%5D={identificador}" in url_antiga, (
                f"{nome}: id {identificador} não estava no edital.py"
            )


def test_traz_as_disciplinas_novas_dos_outros_concursos():
    """São as que destravam PMDF, PCDF, PRF, INSS, BACEN, Correios e BB."""
    novas = {
        "Noções de Informática": 46,
        "Raciocínio Lógico": 4,
        "Direito Penal": 9,
        "Direito Penal Militar": 203,
        "Direito Processual Penal": 10,
        "Administração Geral": 21,
        "Administração Pública": 26,
    }
    for nome, identificador in novas.items():
        assert nome in disciplinas.DISCIPLINAS, f"{nome} não está no registro"
        assert identificador in disciplinas.DISCIPLINAS[nome]


def test_arquivologia_nao_vira_disciplina_separada():
    """O id 20 já está dentro de "Atendimento, Rotinas Administrativas e
    Arquivologia". Registrar de novo faria a mesma questão ser coletada duas
    vezes, com duas matérias diferentes."""
    assert "Arquivologia" not in disciplinas.DISCIPLINAS
    assert 20 in disciplinas.DISCIPLINAS["Atendimento, Rotinas Administrativas e Arquivologia"]


def test_direito_penal_e_penal_militar_sao_disciplinas_distintas():
    """Ramos diferentes, legislações diferentes. Misturar contamina o simulado
    do PMDF, cujo edital lista as duas separadamente."""
    penal = disciplinas.DISCIPLINAS["Direito Penal"]
    militar = disciplinas.DISCIPLINAS["Direito Penal Militar"]
    assert set(penal).isdisjoint(militar)


def test_monta_url_de_busca_com_um_id():
    url = disciplinas.url_de_busca((2,))
    assert "discipline_ids%5B%5D=2" in url
    assert "exclude_nullified=true" in url


def test_monta_url_com_varios_ids():
    """Atendimento junta três disciplinas do QC numa matéria só do edital."""
    url = disciplinas.url_de_busca((20, 187, 174))
    for identificador in (20, 187, 174):
        assert f"discipline_ids%5B%5D={identificador}" in url


def test_nenhum_id_aparece_em_duas_disciplinas():
    """ID repetido faria a mesma questão ser gravada com duas matérias."""
    vistos: dict[int, str] = {}
    for nome, ids in disciplinas.DISCIPLINAS.items():
        for identificador in ids:
            anterior = vistos.get(identificador)
            assert anterior is None, f"id {identificador} em {anterior!r} e {nome!r}"
            vistos[identificador] = nome


def test_disciplina_imprecisa_fica_pausada():
    """O id 61 é "Legislação Estadual" genérico, não legislação do DF.

    Medido no banco: das 1.546 questões coletadas sob "Conhecimentos do DF e
    Legislação", só 25 (2%) eram de órgão do DF — o resto veio de SEDUC-SP,
    Polícia Penal-RS, AL-CE, MPE-GO. Segundo o mapeamento das bancas, a
    legislação distrital exige `subject_ids[]` (LODF, LC 840/2011, Lei
    4.990/2012), que ainda não temos. Até lá, coletar mais é piorar o banco.
    """
    assert "Conhecimentos do DF e Legislação" in disciplinas.PAUSADAS
    assert disciplinas.PAUSADAS["Conhecimentos do DF e Legislação"], "pausa precisa de motivo"


def test_pausada_nao_entra_na_coleta():
    ativas = dict(disciplinas.listar())
    assert "Conhecimentos do DF e Legislação" not in ativas
    assert "Noções de Informática" in ativas


def test_pausada_continua_no_registro_para_nao_perder_o_id():
    """Some da coleta, não do registro: o id e o histórico continuam ali."""
    assert "Conhecimentos do DF e Legislação" in disciplinas.DISCIPLINAS
