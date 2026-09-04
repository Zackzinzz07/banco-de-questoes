"""Orquestrador da coleta na Cebraspe.

Uso:
    python coletar_cebraspe.py            # varre os concursos encerrados
    python coletar_cebraspe.py PRF_21     # só o concurso informado

Camada de orquestração (CLAUDE.md 1.2): coordena as outras sem fazer o
trabalho delas — a rede vem de `scrapers/cebraspe/coletor.py`, a leitura dos
PDFs de `scrapers/cebraspe/parser.py`, a classificação de `config.py`.

Esta fase ARQUIVA e EXTRAI; não grava na tabela `questoes`. O caderno da
Cebraspe identifica só o BLOCO da prova ("CONHECIMENTOS BÁSICOS"), nunca a
matéria, e `db.salvar_questao` exige matéria. Gravar o bloco como se fosse
matéria criaria o mesmo problema que a análise dos editais apontou: rótulo que
não é matéria contaminando o sorteio. A vinculação vem depois, com a taxonomia
e o conteúdo programático do edital.

Arquivar agora, porém, é urgente: edital sai do ar (a FCC retira o caderno em
7 dias, a VUNESP tranca na área do candidato), e o que hoje está aberto pode
não estar quando o parser de edital ficar pronto.
"""

import json
import shutil
import sys
from pathlib import Path

from scrapers import http_utils
from scrapers.cebraspe import coletor, config, parser

PASTA = Path(__file__).resolve().parent / "provas_pdf" / "cebraspe"

# Os 425 concursos ocupam ~2 GB (medido: 4,9 MB por concurso). Encher o disco
# de quem esta usando o projeto e pior do que coletar menos, entao a varredura
# para sozinha antes de chegar no limite.
MINIMO_LIVRE_GB = 3.0


class DiscoCheio(RuntimeError):
    """Espaco em disco abaixo do minimo seguro."""


def espaco_livre_gb(caminho: Path) -> float:
    alvo = caminho if caminho.exists() else caminho.parent
    return shutil.disk_usage(alvo).free / 1024**3


def _extrair(tipo: str, conteudo: bytes) -> list[dict]:
    """Devolve os itens de um arquivo, conforme o tipo classificado."""
    if tipo == config.CADERNO_COM_JUSTIFICATIVA:
        return parser.extrair_itens(conteudo)
    if tipo == config.GABARITO_DEFINITIVO:
        return [
            {"numero": numero, "gabarito": gabarito, "enunciado": "", "justificativa": ""}
            for numero, gabarito in sorted(parser.extrair_gabarito(conteudo).items())
        ]
    return []


def coletar_concurso(sessao, slug: str, pasta_base: Path) -> int:
    """Arquiva os arquivos úteis de um concurso e extrai os itens para JSON.

    Recebe a sessão já aberta (CLAUDE.md 2). Devolve quantos itens extraiu.
    Arquivo já baixado é pulado — 425 concursos são muitas horas, e a retomada
    não pode reconsumir a banda inteira.
    """
    livre = espaco_livre_gb(pasta_base)
    if livre < MINIMO_LIVRE_GB:
        raise DiscoCheio(f"restam {livre:.1f} GB, menos que o minimo de {MINIMO_LIVRE_GB} GB")

    arquivos = coletor.listar_arquivos(sessao, slug)
    uteis = config.aproveitaveis(arquivos)
    editais = [a for a in arquivos if config.classificar(a) == config.EDITAL]
    if not uteis and not editais:
        return 0

    destino = pasta_base / slug / "arquivos"
    destino.mkdir(parents=True, exist_ok=True)

    itens: list[dict] = []
    for arquivo in uteis + editais:
        caminho = destino / arquivo["nome"]
        if caminho.exists():
            conteudo = caminho.read_bytes()
        else:
            try:
                conteudo = coletor.baixar(sessao, slug, arquivo["nome"])
            except Exception as erro:
                print(f"  [SKIP] {arquivo['nome'][:50]}: {erro.__class__.__name__}")
                continue
            caminho.write_bytes(conteudo)
            http_utils.aguardar()

        for item in _extrair(config.classificar(arquivo), conteudo):
            item["concurso"] = slug
            item["arquivo"] = arquivo["nome"]
            itens.append(item)

    if itens:
        alvo = pasta_base / slug / "itens.json"
        alvo.write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(itens)


def coletar_todos(slugs: list[str] | None = None) -> None:
    sessao = http_utils.criar_sessao()
    if slugs is None:
        slugs = [c["slug"] for c in coletor.listar_concursos(sessao)]

    print(f"CEBRASPE — {len(slugs)} concursos a varrer")
    total = 0
    for indice, slug in enumerate(slugs, 1):
        try:
            extraidos = coletar_concurso(sessao, slug, PASTA)
        except DiscoCheio as erro:
            print(f"[PARADO] {erro}. Libere espaco e rode de novo -- retoma daqui.")
            break
        except Exception as erro:
            print(f"[{indice}/{len(slugs)}] {slug}: ERRO ({erro.__class__.__name__}: {erro})")
            continue
        total += extraidos
        if extraidos:
            print(f"[{indice}/{len(slugs)}] {slug}: {extraidos} itens (acumulado {total})")
    print(f"[COMPLETE] {total} itens extraídos de {len(slugs)} concursos.")


def main() -> None:
    coletar_todos(sys.argv[1:] or None)


if __name__ == "__main__":
    main()
