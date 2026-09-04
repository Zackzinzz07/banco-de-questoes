"""Testes da camada de automação da Cebraspe: só HTTP, sem parsing e sem banco.

A sessão é injetada (CLAUDE.md 2), então dá pra exercitar o caminho inteiro
com uma sessão falsa, sem tocar a rede.
"""

import json

import pytest

from scrapers.cebraspe import coletor

LISTA_EVENTOS = [
    {
        "faseEvento": "Encerrados",
        "eventos": [
            {"eventoURL": "PC_DF_24_ADM", "eventoNomeAbreviado": "PC DF 24 ADM", "eventoAno": 2024},
            {"eventoURL": "PRF_21", "eventoNomeAbreviado": "PRF 2021", "eventoAno": 2021},
        ],
    }
]

DETALHE = {
    "eventoURL": "PC_DF_24_ADM",
    "arquivosGabarito": [
        {"nomeArquivo": "022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF", "descricaoArquivo": "Caderno"},
        {"nomeArquivo": "GAB_DEFINITIVO_022_PCDF_001_01.PDF", "descricaoArquivo": "Gabarito"},
    ],
    "arquivosEdital": [
        {
            "nomeArquivo": "ED_1_PCDF_ADM_2024_ABERTURA.PDF",
            "descricaoArquivo": "Edital de abertura",
        },
    ],
}


class _Resposta:
    def __init__(self, dados=None, conteudo=b"", status=200):
        self._dados = dados
        self.content = conteudo
        self.status_code = status

    def json(self):
        return self._dados

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"status {self.status_code}")


class _SessaoFalsa:
    timeout = 5

    def __init__(self):
        self.urls = []

    def get(self, url, timeout=None, **kwargs):
        self.urls.append(url)
        if "fase/encerrado" in url:
            return _Resposta(dados=LISTA_EVENTOS)
        if url.rstrip("/").endswith("PC_DF_24_ADM"):
            return _Resposta(dados=DETALHE)
        if "cdn.cebraspe.org.br" in url:
            return _Resposta(conteudo=b"%PDF-1.4 conteudo")
        return _Resposta(dados={}, status=404)


def test_listar_concursos_devolve_slug_e_nome():
    concursos = coletor.listar_concursos(_SessaoFalsa())
    assert [c["slug"] for c in concursos] == ["PC_DF_24_ADM", "PRF_21"]
    assert concursos[0]["nome"] == "PC DF 24 ADM"


def test_listar_arquivos_junta_gabarito_e_edital():
    arquivos = coletor.listar_arquivos(_SessaoFalsa(), "PC_DF_24_ADM")
    nomes = [a["nome"] for a in arquivos]
    assert "022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF" in nomes
    assert "ED_1_PCDF_ADM_2024_ABERTURA.PDF" in nomes
    assert len(arquivos) == 3


def test_listar_arquivos_marca_a_origem_de_cada_um():
    """Edital e gabarito vêm de campos distintos da API e têm usos distintos:
    o edital alimenta o conteúdo programático; o caderno, o banco de questões."""
    arquivos = coletor.listar_arquivos(_SessaoFalsa(), "PC_DF_24_ADM")
    origens = {a["nome"]: a["origem"] for a in arquivos}
    assert origens["ED_1_PCDF_ADM_2024_ABERTURA.PDF"] == "edital"
    assert origens["GAB_DEFINITIVO_022_PCDF_001_01.PDF"] == "gabarito"


def test_baixar_monta_a_url_do_cdn_com_slug_minusculo():
    """O CDN serve os arquivos sob o slug em minúsculas."""
    sessao = _SessaoFalsa()
    conteudo = coletor.baixar(sessao, "PC_DF_24_ADM", "022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF")
    assert conteudo.startswith(b"%PDF")
    assert sessao.urls[-1] == (
        "https://cdn.cebraspe.org.br/concursos/pc_df_24_adm/arquivos/"
        "022_PCDF_CB1_01_COM_JUSTIFICATIVA.PDF"
    )


def test_baixar_escapa_nome_de_arquivo_com_espaco():
    """Muitos nomes têm espaço e acento (ex.: 'PADRÃO DEFINITIVO DE RESPOSTA - ...')."""
    sessao = _SessaoFalsa()
    coletor.baixar(sessao, "BCB_24", "PADRAO DEFINITIVO DE RESPOSTA.pdf")
    assert " " not in sessao.urls[-1]
    assert "%20" in sessao.urls[-1]


def test_concurso_inexistente_devolve_lista_vazia_sem_estourar():
    assert coletor.listar_arquivos(_SessaoFalsa(), "NAO_EXISTE_99") == []


def test_coletor_nao_faz_parsing_nem_toca_banco():
    """Guarda de camada (CLAUDE.md 1.2): automação só busca, não interpreta."""
    fonte = (coletor.__file__ or "").replace(".pyc", ".py")
    with open(fonte, encoding="utf-8") as arquivo:
        codigo = arquivo.read()
    for proibido in ("BeautifulSoup", "pdfplumber", "psycopg", "INSERT INTO", "import db"):
        assert proibido not in codigo, f"{proibido} não pertence à camada de automação"
    assert json is not None  # mantém o import usado pela fixture acima
