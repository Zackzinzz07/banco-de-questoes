"""Tradução entre o vocabulário do edital e o do banco. Funções puras, sem I/O.

O edital e as fontes de questão nomeiam a mesma matéria de formas diferentes, e
isso travava o multi-concurso inteiro. Medido no edital do PMDF Soldado: das 10
matérias pedidas, 9 devolviam ZERO — não por falta de conteúdo, mas porque o
edital escreve "Noções de Direito Administrativo" e o banco guarda "Direito
Administrativo". O simulado de 120 questões saía com 15; com esta tradução, 89.

Quatro tipos de divergência, cada um com mecanismo próprio:

  prefixo       "Noções de Direito Administrativo" -> "Direito Administrativo"
  decomposição  "Matemática e Raciocínio Lógico"   -> as duas, separadas
  fusão         o banco separa o que o edital junta (mesmo mecanismo)
  bloco         "Conhecimentos Básicos" não é matéria, é rótulo de prova

O GUARDRAIL é o que impede o remédio de virar veneno. Sem ele, "Direito Penal
Militar" casaria com "Direito Penal" — são ramos distintos, com legislação
própria, e o edital do PMDF cobra os dois separadamente. Uma questão de Penal
Militar num simulado de Penal comum corrói a confiança no sistema inteiro, e
uma questão a menos não.

Na dúvida, devolve vazio: erra para EXCLUIR. Simulado menor com aviso é melhor
que simulado errado em silêncio.
"""

import re
import unicodedata

# Prefixos que as bancas usam sem mudar a matéria.
_PREFIXOS = re.compile(
    r"^(nocoes|nocao|fundamentos|elementos|principios|introducao)\s+"
    r"(basicas?\s+|gerais\s+)?(de\s+|do\s+|da\s+|a\s+)?"
)

# Ruído que aparece no nome sem alterar a matéria.
_RUIDO = re.compile(r"\(bloco\s+[ivx]+\)|\boperacional\b|\baplicad[ao]s?\b", re.IGNORECASE)

# Rótulos de prova que agrupam matérias — não são matéria nenhuma.
_BLOCOS = frozenset(
    {
        "conhecimentos basicos",
        "conhecimentos especificos",
        "conhecimentos gerais",
        "conhecimentos complementares",
        "direito",
        "prova objetiva",
    }
)

# Termos que MUDAM o ramo do direito. Se um lado tem e o outro não, veta.
_GUARDRAILS = (
    "militar",
    "processual",
    "trabalho",
    "previdenciari",
    "tributari",
    "eleitoral",
    "internacional",
    "ambiental",
    "publica",
)


def normalizar(nome: str) -> str:
    """Reduz um nome de matéria à sua forma comparável.

    Tira acento, caixa, pontuação, ruído de bloco e prefixo de edital.
    """
    texto = unicodedata.normalize("NFKD", (nome or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = _RUIDO.sub(" ", texto)
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return _PREFIXOS.sub("", texto).strip()


def _compativel(pedido: str, disponivel: str) -> bool:
    """Diz se dois nomes já normalizados podem ser a mesma matéria."""
    if pedido != disponivel:
        return False
    return all((termo in pedido) == (termo in disponivel) for termo in _GUARDRAILS)


def _partes_compostas(normalizado: str) -> list[str]:
    """Quebra "Direito Penal e Processual Penal" nas duas matérias que ela cita.

    O núcleo da primeira parte ("direito") costuma ficar subentendido na
    segunda, então ele é reposto antes de procurar no banco.
    """
    partes = [p.strip() for p in re.split(r"\s+e\s+", normalizado) if p.strip()]
    if len(partes) < 2:
        return []

    nucleo = partes[0].split()[0]
    completas = [partes[0]]
    for parte in partes[1:]:
        completas.append(parte if parte.startswith(nucleo) else f"{nucleo} {parte}")
    return completas


def resolver(materia_do_edital: str, disponiveis: list[str]) -> list[str]:
    """Traduz o nome do edital para os nomes que existem no banco.

    Devolve lista vazia quando não há correspondência segura — nunca um palpite.
    Lista com mais de um nome significa matéria composta: a cota de questões se
    divide entre elas.
    """
    pedido = normalizar(materia_do_edital)
    if not pedido or pedido in _BLOCOS:
        return []

    indice: dict[str, list[str]] = {}
    for nome in disponiveis:
        indice.setdefault(normalizar(nome), []).append(nome)

    for chave, nomes in indice.items():
        if _compativel(pedido, chave):
            return sorted(nomes)

    achadas: list[str] = []
    for parte in _partes_compostas(pedido):
        for chave, nomes in indice.items():
            if _compativel(parte, chave):
                achadas.extend(nomes)
    return sorted(dict.fromkeys(achadas))
