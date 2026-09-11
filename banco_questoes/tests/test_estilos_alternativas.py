"""Os estilos do motor multi-banca precisam imprimir o TEXTO das alternativas.

Todos os quatro desenhavam apenas um marcador vazio — `"( ) Certo ( ) Errado"`
no Cebraspe, `"( ) A  ( ) B  ( ) C  ( ) D  ( ) E"` nos demais — e nunca o
conteúdo das opções. O simulado saía impossível de responder: o enunciado
terminava no meio ("...recomenda-se") e as alternativas simplesmente não
existiam na página.

O gerador antigo (`gerar_simulado.py`) sempre imprimiu, então isso é dívida
só do motor multi-banca.
"""

import pytest

from simulados.estilos.aocp import EstiloAOCP
from simulados.estilos.cebraspe import EstiloCebraspe
from simulados.estilos.fgv import EstiloFGV
from simulados.estilos.iades import EstiloIADES


class _CanvasGravador:
    """Canvas de mentira que só registra o que foi escrito."""

    def __init__(self):
        self.textos: list[str] = []

    def drawString(self, x, y, texto, *a, **k):
        self.textos.append(texto)

    def drawCentredString(self, x, y, texto, *a, **k):
        self.textos.append(texto)

    def stringWidth(self, texto, fonte=None, tamanho=None):
        return len(texto) * 5.0

    def setFont(self, *a, **k):
        pass

    def setFillColor(self, *a, **k):
        pass

    def setStrokeColor(self, *a, **k):
        pass

    def setLineWidth(self, *a, **k):
        pass

    def rect(self, *a, **k):
        pass

    def line(self, *a, **k):
        pass

    @property
    def escrito(self) -> str:
        return " ".join(self.textos)


QUESTAO = {
    "numero": 33,
    "enunciado": "Para manter o bom funcionamento de um antivírus, recomenda-se",
    "opcoes": [
        {"letra": "A", "texto": "acompanhar o site do fabricante do software."},
        {"letra": "B", "texto": "desativar a busca por malwares em tempo real."},
        {"letra": "C", "texto": "manter atualização contínua da solução."},
        {"letra": "D", "texto": "substituir o antivírus por um firewall pessoal."},
        {"letra": "E", "texto": "configurar manualmente a verificação de arquivos."},
    ],
}

CONFIG = {
    "estilo_visual": {"fonte_corpo": "Times New Roman, 9.5pt", "layout_colunas": 2},
    "caracteristicas_prova": {"total_questoes_padrao": 120},
    "estrutura_disciplinas_padrao": [],
}


@pytest.mark.parametrize(
    "classe", [EstiloCebraspe, EstiloFGV, EstiloAOCP, EstiloIADES], ids=lambda c: c.__name__
)
def test_estilo_imprime_o_texto_das_alternativas(classe):
    estilo = classe(CONFIG)
    tela = _CanvasGravador()
    estilo.desenhar_questao(tela, QUESTAO, 50.0, 700.0, 250.0)

    for opcao in QUESTAO["opcoes"]:
        trecho = opcao["texto"].split()[0]
        assert trecho in tela.escrito, (
            f"{classe.__name__} não imprimiu a alternativa {opcao['letra']}"
        )


@pytest.mark.parametrize(
    "classe", [EstiloCebraspe, EstiloFGV, EstiloAOCP, EstiloIADES], ids=lambda c: c.__name__
)
def test_altura_reservada_cobre_a_altura_desenhada(classe):
    """O motor reserva espaço com `calcular_altura_questao` ANTES de desenhar.

    Se a estimativa for menor que o desenho real, a questão seguinte começa
    por cima: num simulado do IADES as alternativas (C), (D) e (E) da questão 1
    saíram DEPOIS do enunciado da questão 2, intercaladas na coluna.

    Alternativa longa quebra em duas linhas; estimar por número de opções
    subestima justamente onde dói.
    """
    LARGURA = 250.0
    estilo = classe(CONFIG)
    questao = dict(
        QUESTAO,
        opcoes=[
            {
                "letra": "A",
                "texto": "acompanhar o site do fabricante do software, "
                "onde serão fornecidas informações a respeito.",
            },
            {
                "letra": "B",
                "texto": "desativar por completo a opção de busca por "
                "malwares em tempo real durante o expediente.",
            },
            {"letra": "C", "texto": "manter atualização contínua da solução de antivírus."},
        ],
    )

    reservada = estilo.calcular_altura_questao(questao, LARGURA)
    desenhada = estilo.desenhar_questao(_CanvasGravador(), questao, 50.0, 700.0, LARGURA)

    assert reservada >= desenhada, (
        f"{classe.__name__} reserva {reservada:.0f}pt e desenha {desenhada:.0f}pt"
    )


def test_cebraspe_certo_errado_nunca_desenha_alternativa_a_e():
    """Bug relatado: simulado do PMDF saiu com opção de múltipla escolha num
    layout Cebraspe C/E, porque a questão sorteada trazia `opcoes` mesmo sendo
    C/E de verdade. `formato` é o que decide agora, não a presença de `opcoes`."""
    estilo = EstiloCebraspe(CONFIG)
    tela = _CanvasGravador()
    questao_ce = dict(QUESTAO, formato="certo_errado")

    estilo.desenhar_questao(tela, questao_ce, 50.0, 700.0, 250.0)

    for opcao in QUESTAO["opcoes"]:
        # Texto completo, não só a 1a palavra: "manter" (opção C) também
        # aparece no enunciado ("Para manter o bom funcionamento..."), o que
        # daria falso positivo checando só a primeira palavra.
        assert opcao["texto"] not in tela.escrito, (
            f"desenhou a alternativa {opcao['letra']} num C/E"
        )
    assert "( ) Certo    ( ) Errado" in tela.escrito


def test_cebraspe_certo_errado_altura_reservada_cobre_a_altura_desenhada():
    questao_ce = dict(QUESTAO, formato="certo_errado")
    estilo = EstiloCebraspe(CONFIG)
    reservada = estilo.calcular_altura_questao(questao_ce, 250.0)
    desenhada = estilo.desenhar_questao(_CanvasGravador(), questao_ce, 50.0, 700.0, 250.0)
    assert reservada >= desenhada
