"""Testes da limpeza de bytes que o PostgreSQL não aceita em colunas text.

Contexto: uma questão do PCI com byte NUL (0x00) no enunciado derrubou a
coleta da categoria `matematica` inteira (~8.841 questões) — o INSERT falhou
e o except do coletor estava no nível da categoria, não da questão.
"""

import sanitizacao


def test_remove_nul_de_string():
    assert sanitizacao.sem_nul("abc\x00def") == "abcdef"


def test_preserva_string_sem_nul():
    assert sanitizacao.sem_nul("enunciado normal") == "enunciado normal"


def test_limpa_nul_dentro_de_dict_de_alternativas():
    alternativas = {"A": "certa\x00", "B": "errada"}
    assert sanitizacao.sem_nul(alternativas) == {"A": "certa", "B": "errada"}


def test_limpa_nul_dentro_de_lista():
    assert sanitizacao.sem_nul(["a\x00", "b"]) == ["a", "b"]


def test_nao_altera_valores_nao_textuais():
    assert sanitizacao.sem_nul(2026) == 2026
    assert sanitizacao.sem_nul(None) is None
