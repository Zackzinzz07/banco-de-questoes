"""Testes do coletor do PCI: o que o parser extrai precisa chegar ao banco.

Usa uma sessão falsa que devolve a fixture salva em disco — sem rede. A
conexão e a sessão já são injetadas na função, então dá pra testar o caminho
de gravação inteiro sem tocar no PCI.
"""
from pathlib import Path

import pytest

import db
from scrapers.pci import coletor_v2

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_pci.html"


class _Resposta:
    def __init__(self, texto, status=200):
        self.text = texto
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"status {self.status_code}")


class _SessaoFalsa:
    """Devolve a fixture na 1ª página e 404 nas seguintes, encerrando o laço."""

    timeout = 5

    def __init__(self, html):
        self._html = html
        self.chamadas = 0

    def get(self, url, timeout=None):
        self.chamadas += 1
        if self.chamadas == 1:
            return _Resposta(self._html)
        return _Resposta("", status=404)


@pytest.fixture
def html():
    if not FIXTURE.exists():
        pytest.skip("fixture pagina_pci.html ainda não capturada")
    return FIXTURE.read_text(encoding="utf-8")


def test_coletor_grava_gabarito_vindo_da_pagina(html):
    con = db.conectar()
    coletor_v2.coletar_tema_v2(
        _SessaoFalsa(html), "portugues", "ortografia", "Ortografia", "", con)

    linha = con.execute(
        "SELECT COUNT(*) AS total, COUNT(gabarito) AS com_gabarito"
        " FROM questoes WHERE fonte='pci'").fetchone()
    assert linha["total"] > 0
    assert linha["com_gabarito"] > 0, "gabarito do simGabaritos não chegou ao banco"
    con.close()


def test_coletor_grava_banca_e_orgao_da_questao(html):
    con = db.conectar()
    coletor_v2.coletar_tema_v2(
        _SessaoFalsa(html), "portugues", "ortografia", "Ortografia", "", con)

    linha = con.execute(
        "SELECT COUNT(banca) AS com_banca, COUNT(orgao) AS com_orgao"
        " FROM questoes WHERE fonte='pci'").fetchone()
    assert linha["com_banca"] > 0, "banca extraída pelo parser foi descartada"
    assert linha["com_orgao"] > 0, "órgão extraído pelo parser foi descartado"
    con.close()
