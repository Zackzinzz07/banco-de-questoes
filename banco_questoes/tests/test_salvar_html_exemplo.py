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


def test_tem_questoes_reconhece_id_do_qc():
    assert ajudante.tem_questoes('<div class="q-id">Q4215783</div>') is True
    assert ajudante.tem_questoes("<div>sem questao aqui</div>") is False
