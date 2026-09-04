"""Testes do orquestrador da coleta na Cebraspe.

Escopo desta fase: baixar e arquivar caderno, gabarito e edital, extraindo os
itens para JSON. As questões NÃO entram na tabela `questoes` ainda — o caderno
da Cebraspe só identifica o BLOCO ("CONHECIMENTOS BÁSICOS"), nunca a matéria,
e `salvar_questao` exige matéria. Gravar o bloco como se fosse matéria criaria
exatamente o problema que a análise dos editais apontou. A vinculação vem
depois, com a taxonomia e o conteúdo programático do edital.
"""

import json

import coletar_cebraspe
import pytest

EVENTOS = [
    {
        "eventos": [
            {"eventoURL": "PC_DF_24_ADM", "eventoNomeAbreviado": "PC DF 24", "eventoAno": 2024},
        ]
    }
]

DETALHE = {
    "arquivosGabarito": [
        {"nomeArquivo": "CAD_COM_JUSTIFICATIVA.PDF", "descricaoArquivo": "Caderno de prova"},
        {"nomeArquivo": "IGNORAR_JUSTIFICATIVAS_DE_ALTERACAO.PDF", "descricaoArquivo": "Recursos"},
    ],
    "arquivosEdital": [
        {"nomeArquivo": "ED_1_ABERTURA.PDF", "descricaoArquivo": "Edital nº 1 – Abertura"},
    ],
}


class _Resposta:
    def __init__(self, dados=None, conteudo=b"", status=200):
        self._dados, self.content, self.status_code = dados, conteudo, status

    def json(self):
        return self._dados

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(self.status_code)


class _SessaoFalsa:
    timeout = 5

    def __init__(self, pdf=b"%PDF-1.4"):
        self.baixados = []
        self._pdf = pdf

    def get(self, url, timeout=None, **kwargs):
        if "fase/encerrado" in url:
            return _Resposta(dados=EVENTOS)
        if url.endswith("PC_DF_24_ADM"):
            return _Resposta(dados=DETALHE)
        self.baixados.append(url.rsplit("/", 1)[-1])
        return _Resposta(conteudo=self._pdf)


@pytest.fixture
def pdf_real():
    from pathlib import Path

    caminho = Path(__file__).parent / "fixtures" / "cebraspe_com_justificativa.pdf"
    if not caminho.exists():
        pytest.skip("fixture da Cebraspe ainda não baixada")
    return caminho.read_bytes()


def test_arquiva_caderno_e_edital_no_disco(tmp_path):
    sessao = _SessaoFalsa()
    coletar_cebraspe.coletar_concurso(sessao, "PC_DF_24_ADM", tmp_path)

    salvos = {p.name for p in (tmp_path / "PC_DF_24_ADM" / "arquivos").iterdir()}
    assert "CAD_COM_JUSTIFICATIVA.PDF" in salvos
    assert "ED_1_ABERTURA.PDF" in salvos, (
        "o edital precisa ser arquivado agora, antes de sair do ar"
    )


def test_nao_baixa_justificativa_de_alteracao_de_gabarito(tmp_path):
    """Documento diferente: traz só os itens mudados em recurso, e renderia zero."""
    sessao = _SessaoFalsa()
    coletar_cebraspe.coletar_concurso(sessao, "PC_DF_24_ADM", tmp_path)
    assert "IGNORAR_JUSTIFICATIVAS_DE_ALTERACAO.PDF" not in sessao.baixados


def test_extrai_os_itens_para_json(tmp_path, pdf_real):
    sessao = _SessaoFalsa(pdf=pdf_real)
    coletar_cebraspe.coletar_concurso(sessao, "PC_DF_24_ADM", tmp_path)

    itens = json.loads((tmp_path / "PC_DF_24_ADM" / "itens.json").read_text(encoding="utf-8"))
    assert len(itens) == 70
    assert {i["gabarito"] for i in itens} == {"CERTO", "ERRADO"}
    assert all(i["concurso"] == "PC_DF_24_ADM" for i in itens)


def test_nao_rebaixa_arquivo_ja_arquivado(tmp_path, pdf_real):
    """Retomada: 425 concursos são muitas horas; rodar de novo não pode
    reconsumir a banda inteira."""
    primeira = _SessaoFalsa(pdf=pdf_real)
    coletar_cebraspe.coletar_concurso(primeira, "PC_DF_24_ADM", tmp_path)
    segunda = _SessaoFalsa(pdf=pdf_real)
    coletar_cebraspe.coletar_concurso(segunda, "PC_DF_24_ADM", tmp_path)
    assert segunda.baixados == []


def test_concurso_sem_arquivo_util_nao_cria_pasta_vazia(tmp_path):
    class _Vazia(_SessaoFalsa):
        def get(self, url, timeout=None, **kwargs):
            if "fase/encerrado" in url:
                return _Resposta(dados=EVENTOS)
            return _Resposta(dados={"arquivosGabarito": [], "arquivosEdital": []})

    coletar_cebraspe.coletar_concurso(_Vazia(), "PC_DF_24_ADM", tmp_path)
    assert not (tmp_path / "PC_DF_24_ADM").exists()


def test_para_quando_o_disco_esta_acabando(tmp_path, monkeypatch, pdf_real):
    """425 concursos ocupam ~2 GB. Encher o disco do usuário seria pior que
    coletar menos, então a varredura para sozinha antes de chegar no limite."""
    monkeypatch.setattr(coletar_cebraspe, "espaco_livre_gb", lambda _: 0.5)
    with pytest.raises(coletar_cebraspe.DiscoCheio):
        coletar_cebraspe.coletar_concurso(_SessaoFalsa(pdf=pdf_real), "PC_DF_24_ADM", tmp_path)


def test_segue_normalmente_quando_ha_espaco(tmp_path, pdf_real):
    assert coletar_cebraspe.espaco_livre_gb(tmp_path) > 0
    coletar_cebraspe.coletar_concurso(_SessaoFalsa(pdf=pdf_real), "PC_DF_24_ADM", tmp_path)
    assert (tmp_path / "PC_DF_24_ADM" / "itens.json").exists()
