"""Desenho das alternativas de uma questão. Compartilhado pelos quatro estilos.

Os estilos do motor multi-banca desenhavam só um marcador vazio no lugar das
opções — `"( ) Certo  ( ) Errado"` no Cebraspe, `"( ) A  ( ) B  ..."` nos
demais — e nunca o texto delas. O simulado saía impossível de responder: o
enunciado terminava no meio ("...recomenda-se") e as alternativas não existiam
na página. O gerador antigo (`gerar_simulado.py`) sempre imprimiu, então a
dívida era só do motor multi-banca.

Vive num módulo próprio, e não em `base.py`, porque os quatro estilos e a
própria base já passam do limite de 250 linhas do CLAUDE.md; assim a mudança
em cada um é de duas linhas, sem piorar a dívida.

Cada estilo passa o SEU `_desenhar_texto_quebrado`, então a tipografia da
banca é preservada — muda o conteúdo, não a identidade visual.
"""

from typing import Any, Callable, Dict, List

# Espaço vertical entre uma alternativa e a seguinte.
ESPACO_ENTRE_OPCOES_PT = 2.0

# Usado quando a questão não traz opções (item certo/errado da Cebraspe, por
# exemplo): mantém a caixa de marcação sem inventar texto.
ALTURA_MARCADOR_PT = 12.0


def desenhar(
    canvas_obj,
    opcoes: List[Dict[str, Any]],
    x: float,
    y: float,
    largura: float,
    escrever: Callable[..., float],
    tamanho_fonte: float = 9.0,
    fonte: str = "Times-Roman",
) -> float:
    """Escreve "(A) texto" em uma linha por alternativa; devolve a altura usada.

    `escrever` é o `_desenhar_texto_quebrado` do estilo chamador, que já sabe
    quebrar linha na largura da coluna daquela banca.

    Lista vazia devolve 0: quem chama decide o que desenhar no lugar (o item
    certo/errado da Cebraspe não tem alternativa nenhuma).
    """
    if not opcoes:
        return 0.0

    altura_total = 0.0
    for opcao in opcoes:
        letra = opcao.get("letra", "")
        texto = opcao.get("texto", "")
        altura = escrever(
            canvas_obj,
            f"({letra}) {texto}",
            x,
            y - altura_total,
            largura,
            tamanho_fonte=tamanho_fonte,
            fonte=fonte,
        )
        altura_total += altura + ESPACO_ENTRE_OPCOES_PT
    return altura_total


def altura(
    opcoes: List[Dict[str, Any]],
    largura: float,
    quebrar: Callable[..., List[str]],
    tamanho_fonte: float = 9.0,
) -> float:
    """Estima a altura que `desenhar` vai ocupar, usando a MESMA quebra de linha.

    O motor reserva espaco com `calcular_altura_questao` antes de desenhar. Se
    a estimativa for menor que o desenho, a questao seguinte comeca por cima:
    num simulado do IADES as alternativas (C), (D) e (E) da questao 1 sairam
    depois do enunciado da questao 2, intercaladas na coluna.

    Contar opcoes e multiplicar por uma altura fixa subestima justamente onde
    dói -- alternativa longa quebra em duas ou tres linhas.
    """
    if not opcoes:
        return ALTURA_MARCADOR_PT

    total = 0.0
    for opcao in opcoes:
        texto = f"({opcao.get('letra', '')}) {opcao.get('texto', '')}"
        linhas = quebrar(texto, largura, tamanho_fonte)
        total += len(linhas) * tamanho_fonte * 1.4 + ESPACO_ENTRE_OPCOES_PT
    return total
