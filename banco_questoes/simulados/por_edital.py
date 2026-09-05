"""Monta um simulado com a FORMA de um edital, usando questões de qualquer banca.

É o modo treino: mesmo número de questões e mesma proporção de matérias que a
prova real cobra, mas o conteúdo vem do acervo inteiro — prefeituras, conselhos,
outras bancas. Serve para treinar a distribuição da prova antes de ela existir,
e é diferente do modo "prova real", que reproduz um caderno oficial item a item.

Três coisas que este módulo NÃO faz, e cada uma tem cicatriz:

  Não completa com questão de outra matéria. O gerador antigo tinha um
  "backfill genérico" que, ao não achar nada para uma matéria, puxava questão
  de qualquer lugar — foi assim que um simulado do PMDF saiu com Lei Municipal
  de Estância/SE debaixo de "Legislação Específica da PMDF e RIDE".

  Não inventa correspondência de nome. Quem traduz é `taxonomia`, que erra para
  excluir: na dúvida devolve vazio, e o guardrail impede que Direito Penal
  Militar vire Direito Penal.

  Não esconde o buraco. Devolve em `lacunas` o que faltou, matéria por matéria,
  para quem chamou avisar em vez de entregar um simulado torto em silêncio.
"""

from dataclasses import dataclass, field
from typing import Any

import db
import taxonomia


@dataclass
class Simulado:
    """O que foi montado, e o que não deu para montar."""

    questoes: list[dict[str, Any]] = field(default_factory=list)
    lacunas: dict[str, int] = field(default_factory=dict)

    @property
    def completo(self) -> bool:
        return not self.lacunas


def _dividir(quantidade: int, partes: int) -> list[int]:
    """Reparte uma cota entre N matérias, sobrando o resto para as primeiras."""
    base, resto = divmod(quantidade, partes)
    return [base + (1 if i < resto else 0) for i in range(partes)]


def montar(con, pesos: dict[str, int], quantidade: int | None = None) -> Simulado:
    """Monta o simulado a partir do quadro de matérias do edital.

    `pesos` é `{nome no edital: quantas questões}` — o que sai direto do YAML em
    `configuracoes_editais/`. A conexão vem aberta (CLAUDE.md 2).

    `quantidade` existe só para simulados menores que a prova inteira; a
    proporção entre matérias é preservada.
    """
    total_edital = sum(pesos.values()) or 1
    escala = (quantidade / total_edital) if quantidade else 1.0

    disponiveis = [
        linha["materia"]
        for linha in con.execute("SELECT DISTINCT materia FROM questoes").fetchall()
        if linha["materia"]
    ]

    simulado = Simulado()
    vistos: set[int] = set()

    for materia_do_edital, peso in pesos.items():
        alvo = round(peso * escala)
        if alvo <= 0:
            continue

        equivalentes = taxonomia.resolver(materia_do_edital, disponiveis)
        if not equivalentes:
            simulado.lacunas[materia_do_edital] = alvo
            continue

        colhidas: list[dict[str, Any]] = []
        for nome, cota in zip(equivalentes, _dividir(alvo, len(equivalentes))):
            for questao in db.sortear_questoes(con, nome, cota):
                if questao["id"] not in vistos:
                    vistos.add(questao["id"])
                    colhidas.append(questao)

        simulado.questoes.extend(colhidas)
        if len(colhidas) < alvo:
            simulado.lacunas[materia_do_edital] = alvo - len(colhidas)

    return simulado
