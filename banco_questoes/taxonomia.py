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

# Sinônimos e variações de gênero/grau que a normalização por regex não
# resolve — palavra diferente da do banco, ou adjetivo no lugar do
# substantivo por concordância com outra matéria da mesma lista ("Raciocínio
# Lógico e Matemático" concorda no masculino com "Raciocínio", mas o banco
# guarda o substantivo "Matemática"). Achado real no edital do PMDF: sem
# isso, "Língua Inglesa" virava lacuna e "Matemático" sumia sem aviso porque
# a cota inteira ia para "Raciocínio Lógico".
_SINONIMOS = {
    "lingua inglesa": "ingles",
    "lingua espanhola": "espanhol",
    "matematico": "matematica",
    "portugues": "lingua portuguesa",
    # Frase inteira do edital do PRF (2026): "CTB" e "CONTRAN" são as siglas
    # da mesma "Legislação de Trânsito" que o banco guarda — sem isso, 30 das
    # 120 questões do PRF (25% da prova) viravam lacuna.
    "legislacao especial de transito ctb e contran": "legislacao de transito",
    # PRF pede "Inglês ou Espanhol"; o acervo só tem "Inglês" catalogado —
    # mapeia para o que existe em vez de zerar os dois.
    "lingua estrangeira ingles ou espanhol": "ingles",
}


def _canonico(normalizado: str) -> str:
    return _SINONIMOS.get(normalizado, normalizado)


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
    if _canonico(pedido) != _canonico(disponivel):
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
    candidatas = [partes[0]]
    for parte in partes[1:]:
        # A parte pode vir completa ("Matemática E RACIOCÍNIO LÓGICO") ou com o
        # núcleo subentendido ("Direito Penal e PROCESSUAL PENAL"). Só o banco
        # decide qual das duas existe, então as duas são oferecidas.
        candidatas.append(parte)
        if not parte.startswith(nucleo):
            candidatas.append(f"{nucleo} {parte}")
    return candidatas


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


# Ordem pedagógica dentro de Língua Portuguesa (chave = `categoria` como as
# fontes gravam, já normalizada). Medido no relatório de bug do simulado do
# PMDF: a prova real começa por interpretação de texto, nunca por gramática.
# Só Português tem matriz por ora — outra matéria sem entrada aqui mantém a
# ordem original em vez de arriscar um palpite (mesmo princípio do guardrail
# de `resolver`: na dúvida, não inventa).
_ORDEM_PORTUGUES = {
    "interpretacao de textos": 0,
    "interpretacao de texto": 0,
    "compreensao de texto": 0,
    "compreensao de textos": 0,
    "tipologia textual": 0,
    "ortografia": 1,
    "acentuacao": 1,
    "fonologia": 1,
    "vocabulario": 1,
    "morfologia": 2,
    "classes de palavras": 2,
    "sintaxe": 3,
    "pontuacao": 3,
    "regencia": 3,
    "concordancia": 3,
    "crase": 3,
}


def ordenar_questoes(questoes: list[dict], materia: str) -> list[dict]:
    """Reordena pela precedência pedagógica real de uma prova, quando conhecida.

    `questoes` vem no formato de `db.sortear_questoes` (cada uma com
    `categoria`). Questão sem `categoria` reconhecida, ou matéria sem matriz
    definida, mantém sua posição relativa original (sort estável) — nunca
    inventa uma ordem sem dado por trás.
    """
    if "portugues" not in normalizar(materia):
        return list(questoes)

    def posicao(questao: dict) -> int:
        return _ORDEM_PORTUGUES.get(normalizar(questao.get("categoria") or ""), 99)

    return sorted(questoes, key=posicao)


def agrupar_por_texto_associado(questoes: list[dict]) -> list[dict]:
    """Reordena para que questões do mesmo texto-base fiquem contíguas.

    Preserva a ordem de primeira aparição de cada grupo. Questão sem texto
    associado (a maioria) vira grupo de uma questão só e mantém sua posição
    relativa — nunca é misturada com outra questão sem texto.
    """
    grupos: dict[str, list[dict]] = {}
    ordem: list[str] = []
    for i, questao in enumerate(questoes):
        chave = questao.get("texto_associado") or f"__solo_{i}__"
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(questao)
    return [questao for chave in ordem for questao in grupos[chave]]
