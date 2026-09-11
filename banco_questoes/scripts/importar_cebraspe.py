"""Vincula itens já arquivados da Cebraspe (`provas_pdf/cebraspe/<slug>/itens.json`,
ver `coletar_cebraspe.py`) à tabela `questoes`, descobrindo a matéria de cada
item pela posição dele na prova.

Uso:
    python -m scripts.importar_cebraspe <slug_cebraspe> <slug_edital> [cargo]

`slug_cebraspe` é a pasta em `provas_pdf/cebraspe/` (o slug que a banca usa,
ex: "prf_21"). `slug_edital` é o arquivo em `configuracoes_editais/` (ex:
"prf"). Os dois divergem — um é da banca, outro é nosso — e forçar
correspondência automática entre eles seria adivinhar.

Estratégia de matéria: a Cebraspe numera os itens de 1 a N na MESMA ordem em
que declara as matérias no edital (é assim que a banca sempre imprime a
prova — achado já usado manualmente em `configuracoes_editais/prf.yaml`).
Isso dá faixas [(1, 15, "Língua Portuguesa"), (16, 20, "Língua Inglesa"), ...]
a partir do peso de cada matéria. Item cuja numeração cai fora de toda faixa
não é gravado — matéria incerta é motivo de exclusão, não de palpite
(CLAUDE.md: "erra para excluir").

LIMITAÇÃO CONHECIDA: se o edital tiver mais de um cargo, cada cargo tem seu
próprio caderno numerado a partir de 1 (coletar_cebraspe.py já avisa disso), mas
`itens.json` mistura os itens de todos os cargos do concurso sem marcar qual
item é de qual — só guarda o nome do PDF de origem (`arquivo`), que não segue
um padrão confiável entre certames para inferir o cargo automaticamente. Por
ora, `--cargo` é aceito para escolher QUAL faixa aplicar, mas a lista de
`itens` que este módulo recebe já precisa vir filtrada para aquele cargo (na
mão, ou por uma etapa futura que separe por `arquivo`); do contrário, itens de
cargos diferentes com o mesmo número colidem na mesma faixa.
"""

import json
import sys
from pathlib import Path
from typing import Any

try:
    import db
    import edital_loader
except ImportError:  # rodando de fora da pasta do projeto
    from banco_questoes import db, edital_loader

PASTA_CEBRASPE = Path(__file__).resolve().parent.parent / "provas_pdf" / "cebraspe"

_GABARITO = {"CERTO": "C", "ERRADO": "E"}


def calcular_faixas(pesos: dict[str, int]) -> list[tuple[int, int, str]]:
    """[(início, fim, matéria), ...] a partir da ordem e peso do edital."""
    faixas = []
    inicio = 1
    for materia, qtd in pesos.items():
        faixas.append((inicio, inicio + qtd - 1, materia))
        inicio += qtd
    return faixas


def resolver_materia(numero: int, faixas: list[tuple[int, int, str]]) -> str | None:
    """Matéria do item `numero`, ou None se cair fora de toda faixa.

    Fora de faixa é sinal de numeração que não bate com o edital (cargo
    errado, ou o caderno tem mais itens do que o esperado) — não é um caso
    para adivinhar a matéria mais próxima.
    """
    for inicio, fim, materia in faixas:
        if inicio <= numero <= fim:
            return materia
    return None


def _questao_do_item(item: dict[str, Any], materia: str, ano: Any, orgao: str) -> dict[str, Any]:
    gabarito = _GABARITO.get((item.get("gabarito") or "").upper())
    return {
        "id_qc": f"cebraspe_{item['concurso']}_{item['arquivo']}_{item['numero']}",
        "enunciado": item["enunciado"],
        "alternativas": {"C": "Certo", "E": "Errado"},
        "gabarito": gabarito,
        "comentario": item.get("justificativa") or None,
        "materia": materia,
        "banca": "Cebraspe",
        "orgao": orgao,
        "ano": ano,
        "fonte": "cebraspe",
        "formato": "certo_errado",
    }


def importar(
    con, itens: list[dict[str, Any]], slug_edital: str, cargo: str | None = None
) -> dict[str, int]:
    """Grava em `questoes` os itens cuja matéria dá pra resolver com segurança.

    Devolve {"salvas", "duplicadas", "sem_materia"} — "sem_materia" é o
    guardrail funcionando, não um erro.
    """
    edital = edital_loader.carregar_edital(slug_edital)
    if not edital:
        raise ValueError(f"edital '{slug_edital}' não encontrado em configuracoes_editais/")

    cargos = edital.get("cargos", {})
    if cargo is None:
        if len(cargos) != 1:
            raise ValueError(
                f"edital '{slug_edital}' tem {len(cargos)} cargos; informe cargo "
                "(cada cargo tem numeração própria, não dá pra adivinhar qual usar)"
            )
        cargo = next(iter(cargos))

    pesos = edital_loader.obter_pesos(slug_edital, cargo)
    if not pesos:
        raise ValueError(f"cargo '{cargo}' não encontrado no edital '{slug_edital}'")

    faixas = calcular_faixas(pesos)
    ano = edital.get("ano")
    orgao = edital.get("orgao", "")

    contagem = {"salvas": 0, "duplicadas": 0, "sem_materia": 0}
    for item in itens:
        materia = resolver_materia(item["numero"], faixas)
        if materia is None:
            contagem["sem_materia"] += 1
            continue
        if db.salvar_questao(con, _questao_do_item(item, materia, ano, orgao)):
            contagem["salvas"] += 1
        else:
            contagem["duplicadas"] += 1
    return contagem


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python -m scripts.importar_cebraspe <slug_cebraspe> <slug_edital> [cargo]")
        sys.exit(1)

    slug_cebraspe, slug_edital = sys.argv[1], sys.argv[2]
    cargo = sys.argv[3] if len(sys.argv) > 3 else None

    caminho = PASTA_CEBRASPE / slug_cebraspe / "itens.json"
    if not caminho.exists():
        print(f"Erro: {caminho} não existe. Rode coletar_cebraspe.py primeiro.")
        sys.exit(1)
    itens = json.loads(caminho.read_text(encoding="utf-8"))

    con = db.conectar()
    try:
        contagem = importar(con, itens, slug_edital, cargo)
    finally:
        con.close()

    print(
        f"[{slug_edital}] {contagem['salvas']} salvas, "
        f"{contagem['duplicadas']} duplicadas, {contagem['sem_materia']} sem matéria"
    )


if __name__ == "__main__":
    main()
