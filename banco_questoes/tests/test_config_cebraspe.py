"""Testes da classificação de arquivos da Cebraspe.

Os nomes de arquivo são inconsistentes — certames recentes usam hash SHA-256
sem semântica nenhuma (`195BA59646CF...PDF`). A `descricaoArquivo` que a API
devolve é a fonte confiável, e ainda traz a faixa de itens de cada fragmento
("PROVA OBJETIVA - ITENS DE 1 A 8 - LÍNGUA ESTRANGEIRA").

Todos os exemplos abaixo são reais, tirados da API em 03/09/2026.
"""

from scrapers.cebraspe import config


def _arquivo(nome, descricao=""):
    return {"nome": nome, "descricao": descricao, "origem": "gabarito"}


def test_reconhece_caderno_com_justificativa_embutida():
    """O melhor arquivo: enunciado, gabarito e justificativa da banca juntos."""
    item = _arquivo("022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF", "Caderno de prova")
    assert config.classificar(item) == "caderno_com_justificativa"


def test_nao_confunde_com_justificativas_de_alteracao_de_gabarito():
    """`JUSTIFICATIVAS_DE_ALTERACOES` traz só os itens mudados em recurso —
    é outro documento, e cair no mesmo balde faria o parser render zero item."""
    item = _arquivo(
        "PRF_18_JUSTIFICATIVAS_DE_ALTERAES_DE_GABARITO.PDF",
        "Justificativas de alterações de gabarito",
    )
    assert config.classificar(item) == "justificativa_de_alteracao"


def test_reconhece_gabarito_definitivo_pelo_nome():
    item = _arquivo("GAB_DEFINITIVO_578_PRF_001_01.PDF", "Gabarito definitivo")
    assert config.classificar(item) == "gabarito_definitivo"


def test_reconhece_gabarito_preliminar():
    item = _arquivo("GAB_PRELIMINAR_632_PRF_001_01.PDF", "Gabarito preliminar")
    assert config.classificar(item) == "gabarito_preliminar"


def test_reconhece_caderno_de_prova_pela_descricao():
    """O nome `578_PRF_ESP_02.PDF` não diz nada; a descrição diz tudo."""
    item = _arquivo("578_PRF_ESP_02.PDF", "PROVA OBJETIVA - ITENS DE 1 A 8 - LÍNGUA ESTRANGEIRA")
    assert config.classificar(item) == "caderno"


def test_reconhece_edital_mesmo_com_nome_em_hash():
    """Certames recentes nomeiam o arquivo com SHA-256; só a descrição informa."""
    item = {
        "nome": "195BA59646CF44425A6CCBA8C096B95F903389CAA72252914345F725BA6C4D77.PDF",
        "descricao": "Edital nº 1 – Abertura de inscrições",
        "origem": "edital",
    }
    assert config.classificar(item) == "edital"


def test_prorrogacao_de_validade_nao_e_edital_aproveitavel():
    """Aviso administrativo: não traz conteúdo programático nem quadro de provas."""
    item = {
        "nome": "195BA59646CF44425A6CCBA8C096B95F903389CAA72252914345F725BA6C4D77.PDF",
        "descricao": "Edital nº 118 – Prorrogação da validade do concurso",
        "origem": "edital",
    }
    assert config.classificar(item) == "outro"


def test_reconhece_padrao_de_resposta_da_discursiva():
    item = _arquivo("PRF_21_PADRAO_DE_RESPOSTA_DEFINITIVO.PDF", "PADRÃO DE RESPOSTA DEFINITIVO")
    assert config.classificar(item) == "padrao_de_resposta"


def test_arquivo_irreconhecivel_nao_vira_palpite():
    """Sem sinal, devolve `outro` — inventar tipo contamina a coleta."""
    item = _arquivo("ABCDEF123.PDF", "Comunicado")
    assert config.classificar(item) == "outro"


def test_faixa_de_itens_sai_da_descricao():
    item = _arquivo("578_PRF_ESP_02.PDF", "PROVA OBJETIVA - ITENS DE 1 A 8 - LÍNGUA ESTRANGEIRA")
    assert config.faixa_de_itens(item) == (1, 8)


def test_faixa_de_itens_ausente_devolve_none():
    item = _arquivo("022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF", "Caderno de prova")
    assert config.faixa_de_itens(item) is None


def test_aproveitaveis_prioriza_o_caderno_com_justificativa():
    """Quando o concurso publica a versão justificada, ela dispensa o gabarito
    separado: enunciado e resposta já vêm no mesmo arquivo."""
    arquivos = [
        _arquivo("X_COM_JUSTIFICATIVA.PDF", "Caderno"),
        _arquivo("GAB_DEFINITIVO_X.PDF", "Gabarito definitivo"),
        _arquivo("Y_ESP_01.PDF", "PROVA OBJETIVA - ITENS DE 1 A 50"),
    ]
    tipos = {config.classificar(a) for a in config.aproveitaveis(arquivos)}
    assert "caderno_com_justificativa" in tipos
    assert "justificativa_de_alteracao" not in tipos


def test_edital_de_abertura_e_normativo():
    """É o edital de abertura que carrega o conteúdo programático."""
    item = {
        "nome": "ED_1_PCDF_ADM_2024_ABERTURA.PDF",
        "descricao": "Edital nº 1 – Abertura",
        "origem": "edital",
    }
    assert config.classificar(item) == "edital"


def test_retificacao_tambem_e_normativa():
    """Retificação altera o conteúdo programático e o quadro de provas."""
    item = {
        "nome": "ED_4_PCDF_ADM_2024_RETIFICACOES.PDF",
        "descricao": "Edital nº 4 – Retificações",
        "origem": "edital",
    }
    assert config.classificar(item) == "edital"


def test_aviso_de_resultado_nao_e_edital_aproveitavel():
    """São listas de candidatos: 31 dos 33 MB baixados da PCDF 2024 eram isso.

    Arquivar tudo custaria ~14 GB nos 425 concursos, contra ~640 MB só com o
    que tem conteúdo programático.
    """
    for nome, descricao in (
        ("ED_10_PCDF_2024_Res_final_obj_prov_disc.pdf", "Edital nº 10 – Resultado final"),
        ("ED_8_PCDF_ADM_2024_RES_PROV_OBJ.PDF", "Edital nº 8 – Resultado provisório"),
        ("PCDF_ADM_2024_REL_PROV_INSC_DEF.PDF", "Relatório de inscrições deferidas"),
        ("PC DF GESTOR DE APOIO.pdf", "Relatório de movimentação financeira"),
        ("ED_16_PCDF_2024_Res_prov_desemp.pdf", "Edital nº 16 – Resultado no desempate"),
    ):
        item = {"nome": nome, "descricao": descricao, "origem": "edital"}
        assert config.classificar(item) == "outro", f"{descricao!r} não deveria ser arquivado"


def test_aviso_de_resultado_nao_vira_caderno_por_conter_prova_objetiva():
    """Caso real (AGSUS_25_CCE): a descrição "Edital nº 7 – Resultado final na
    prova objetiva e a convocação..." casava com a regra de CADERNO por causa
    de "prova objetiva", e o arquivo entrava na lista de aproveitáveis."""
    item = {
        "nome": "C5FF2BA57D467D34F61D023FCAAFBB1C0E19DC9A43C47AF45293F5439A527B86.html",
        "descricao": "Edital nº 7 – Resultado final na prova objetiva e a convocação",
        "origem": "gabarito",
    }
    assert config.classificar(item) == "outro"


def test_gabarito_continua_valido_mesmo_falando_em_resultado():
    """A guarda de não-normativo não pode derrubar gabarito: a banca costuma
    publicar "resultado" e "gabarito" no mesmo aviso."""
    item = {
        "nome": "GAB_DEFINITIVO_578_PRF_001_01.PDF",
        "descricao": "Gabarito definitivo e resultado da prova objetiva",
        "origem": "gabarito",
    }
    assert config.classificar(item) == "gabarito_definitivo"


def test_arquivo_que_nao_e_pdf_fica_de_fora_dos_aproveitaveis():
    """A Cebraspe publica parte dos documentos em HTML; o parser lê PDF."""
    arquivos = [
        _arquivo("CAD_01.html", "PROVA OBJETIVA - ITENS DE 1 A 50"),
        _arquivo("CAD_02.PDF", "PROVA OBJETIVA - ITENS DE 51 A 100"),
    ]
    nomes = {a["nome"] for a in config.aproveitaveis(arquivos)}
    assert nomes == {"CAD_02.PDF"}
