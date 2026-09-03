"""Limpeza de valores antes da gravação. Funções puras, sem I/O.

O PostgreSQL rejeita o byte NUL (0x00) em colunas `text`. Páginas de origem
às vezes trazem esse byte no meio do enunciado, e o INSERT estoura com
`ValueError: A string literal cannot contain NUL (0x00) characters.`

Isso já custou caro: uma questão de `matematica` no PCI derrubou a coleta da
categoria inteira (~8.841 questões), porque o tratamento de erro do coletor
estava no nível da categoria em vez do da questão.
"""

NUL = "\x00"


def sem_nul(valor):
    """Devolve `valor` sem bytes NUL, descendo por dicts e listas.

    Tipos não textuais (int, None, float, bool) voltam intactos.
    """
    if isinstance(valor, str):
        return valor.replace(NUL, "")
    if isinstance(valor, dict):
        return {chave: sem_nul(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return type(valor)(sem_nul(item) for item in valor)
    return valor
