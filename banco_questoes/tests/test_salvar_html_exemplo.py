"""Testes do ajudante de login/captura de fixture do QConcursos."""
import salvar_html_exemplo as ajudante


def test_esta_logado_falso_quando_ha_link_de_entrar():
    """A página pública do QC já lista questões mesmo deslogado — por isso a
    presença de questão não serve como sinal de login. O link /conta/entrar
    só existe enquanto ninguém está logado."""
    html = '<a data-permissions="account" href="/conta/entrar">Entrar</a>'
    assert ajudante.esta_logado(html) is False


def test_esta_logado_falso_quando_marcado_signed_out():
    html = '<div class="q-mobile-login-link q-mobile-signed-out">Entrar</div>'
    assert ajudante.esta_logado(html) is False


def test_esta_logado_verdadeiro_sem_marcadores_de_deslogado():
    html = '<div class="q-user-menu"><a href="/conta/meus-dados">Meus dados</a></div>'
    assert ajudante.esta_logado(html) is True


def test_esta_logado_falso_para_html_vazio():
    assert ajudante.esta_logado("") is False


class _PaginaNavegando:
    """Página que está trocando de URL — content() falha nesse instante."""

    def content(self):
        from playwright.sync_api import Error as ErroPlaywright
        raise ErroPlaywright(
            "Page.content: Unable to retrieve content because the page is"
            " navigating and changing the content.")


class _PaginaOk:
    def content(self):
        return "<html>logado</html>"


def test_conteudo_seguro_devolve_vazio_quando_pagina_esta_navegando():
    """Durante o login a página navega várias vezes; ler o HTML nesse instante
    levanta erro do Playwright e não pode derrubar a espera pelo login."""
    assert ajudante.conteudo_seguro(_PaginaNavegando()) == ""


def test_conteudo_seguro_devolve_html_quando_pagina_estavel():
    assert ajudante.conteudo_seguro(_PaginaOk()) == "<html>logado</html>"


def test_aguardar_login_nao_quebra_com_pagina_navegando():
    """A espera precisa sobreviver à navegação: devolve False no fim do tempo,
    nunca uma exceção."""
    assert ajudante.aguardar_login(
        _PaginaNavegando(), tentativas=2, intervalo=0) is False


def test_tem_questoes_reconhece_id_do_qc():
    assert ajudante.tem_questoes('<div class="q-id">Q4215783</div>') is True
    assert ajudante.tem_questoes("<div>sem questao aqui</div>") is False
