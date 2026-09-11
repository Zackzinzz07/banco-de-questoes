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

from reportlab.lib import colors

# Espaço vertical entre uma alternativa e a seguinte.
ESPACO_ENTRE_OPCOES_PT = 2.0

# Usado quando a questão não traz opções (item certo/errado da Cebraspe, por
# exemplo): mantém a caixa de marcação sem inventar texto.
ALTURA_MARCADOR_PT = 12.0

# Altura ocupada pela linha de identificação da fonte original
ALTURA_METADADOS_PT = 14.0

# Altura ocupada pelo título divisor de matéria
ALTURA_DIVISOR_MATERIA_PT = 24.0


def formatar_origem(questao_data: Dict[str, Any]) -> str:
    """Formata a linha de origem real no padrão: [BANCA] · [CONCURSO] · [ANO]."""
    banca = questao_data.get("banca") or "Banca não informada"
    ano = questao_data.get("ano")
    orgao = questao_data.get("orgao")
    cargo = questao_data.get("cargo")

    partes = [str(banca)]

    concurso = ""
    if orgao and cargo and cargo != "Não informado":
        concurso = f"{orgao} / {cargo}"
    elif orgao:
        concurso = str(orgao)
    elif cargo and cargo != "Não informado":
        concurso = str(cargo)

    if concurso:
        partes.append(concurso)
    if ano:
        partes.append(str(ano))

    return " · ".join(partes)


def desenhar_origem(
    canvas_obj,
    questao_data: Dict[str, Any],
    x: float,
    y: float,
    largura: float,
) -> float:
    """Desenha linha discreta com a origem real da questão (#475569, 7.5pt)."""
    texto = formatar_origem(questao_data)
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(colors.HexColor("#475569"))
    while texto and canvas_obj.stringWidth(texto, "Helvetica", 7.5) > largura:
        texto = texto[:-4] + "..."
    canvas_obj.drawString(x, y - 2.0, texto)
    return ALTURA_METADADOS_PT


def desenhar_divisor_materia(
    canvas_obj,
    materia: str,
    x: float,
    y: float,
    largura: float,
    fonte: str = "Helvetica-Bold",
) -> float:
    """Desenha cabeçalho divisor com o nome da matéria em CAIXA ALTA E NEGRITO."""
    if not materia:
        return 0.0
    titulo = materia.strip().upper()
    canvas_obj.setFont(fonte, 10.5)
    canvas_obj.setFillColor(colors.black)
    canvas_obj.drawString(x, y - 10.0, titulo)

    # Linha divisória sutil
    canvas_obj.setLineWidth(0.6)
    canvas_obj.setStrokeColor(colors.HexColor("#64748b"))
    canvas_obj.line(x, y - 14.0, x + largura, y - 14.0)
    return ALTURA_DIVISOR_MATERIA_PT


# Mantém alias para compatibilidade
formatar_metadados = formatar_origem
desenhar_metadados = desenhar_origem


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
