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

# Medicao atualizada com 36 concursos arquivados: 6,8 MB cada, ~2,9 GB nos 425
# (a primeira estimativa, de 4,9 MB, veio de uma amostra pequena demais).
# Encher o disco de quem usa o projeto e pior do que coletar menos, entao a
# varredura para sozinha antes de chegar no limite.
# Reduzido de 5.0 para 2.0 GB gracas ao auto-purge de PDFs brutos apos extracao
MINIMO_LIVRE_GB = 2.0


class DiscoCheio(RuntimeError):
    """Espaco em disco abaixo do minimo seguro."""


def espaco_livre_gb(caminho: Path) -> float:
    alvo = caminho if caminho.exists() else caminho.parent
    return shutil.disk_usage(alvo).free / 1024**3


PREFIXO_GABARITO = "GAB_DEFINITIVO_"


def _par_de_gabarito(nome_do_caderno: str, disponiveis: dict[str, str]) -> str | None:
    """Acha o gabarito do caderno: a banca nomeia `GAB_DEFINITIVO_<caderno>`.

    Casar por numero de item dentro do concurso seria errado: cada cargo tem
    seu caderno e TODOS numeram de 1 a 120, entao o item 61 de um cargo nao e
    o item 61 do outro. O nome do arquivo e o unico vinculo confiavel --
    medido: 82% dos gabaritos arquivados tem caderno de mesmo nome.
    """
    return disponiveis.get((PREFIXO_GABARITO + nome_do_caderno).upper())


def _itens_do_caderno(conteudo: bytes, gabaritos: dict[int, str]) -> list[dict]:
    """Junta as duas metades da questao: enunciado do caderno, resposta do gabarito."""
    itens = parser.extrair_enunciados(conteudo)
    for item in itens:
        item["gabarito"] = gabaritos.get(item["numero"])
        item["justificativa"] = ""
    return itens


def coletar_concurso(sessao, slug: str, pasta_base: Path, manter_pdfs: bool = False) -> int:
    """Arquiva os arquivos úteis de um concurso e extrai os itens para JSON.

    Recebe a sessão já aberta (CLAUDE.md 2). Devolve quantos itens extraiu.
    Arquivo já baixado é pulado — 425 concursos são muitas horas, e a retomada
    não pode reconsumir a banda inteira.
    Se manter_pdfs for False (padrão), os PDFs brutos de gabaritos e cadernos
    são excluídos após a extração para manter o banco leve (economia de 98%).
    """
    livre = espaco_livre_gb(pasta_base)
    if livre < MINIMO_LIVRE_GB:
        raise DiscoCheio(f"restam {livre:.1f} GB, menos que o minimo de {MINIMO_LIVRE_GB} GB")

    arquivos = coletor.listar_arquivos(sessao, slug)
    uteis = config.aproveitaveis(arquivos)
    todos_editais = [
        a
        for a in arquivos
        # A Cebraspe publica parte dos avisos em HTML; o parser le PDF.
        if a["nome"].lower().endswith(".pdf") and config.classificar(a) == config.EDITAL
    ]
    # Filtro estrito: prioriza Edital de Abertura para nao baixar retificacoes de datas
    editais_abertura = [
        e
        for e in todos_editais
        if "ABERTURA" in (e.get("nome", "") + " " + e.get("descricao", "")).upper()
    ]
    editais = editais_abertura[:1] if editais_abertura else todos_editais[:1]

    if not uteis and not editais:
        return 0

    alvo_itens = pasta_base / slug / "itens.json"
    alvo_gab = pasta_base / slug / "gabarito.json"
    arquivos_ja_processados: set[str] = set()
    itens_existentes: list[dict] = []
    if alvo_itens.exists():
        try:
            itens_existentes = json.loads(alvo_itens.read_text(encoding="utf-8"))
            arquivos_ja_processados.update(
                it.get("arquivo") for it in itens_existentes if "arquivo" in it
            )
        except Exception:
            pass
    if alvo_gab.exists():
        try:
            gabs_existentes = json.loads(alvo_gab.read_text(encoding="utf-8"))
            arquivos_ja_processados.update(gabs_existentes.keys())
        except Exception:
            pass

    destino = pasta_base / slug / "arquivos"
    destino.mkdir(parents=True, exist_ok=True)

    baixados: dict[str, bytes] = {}
    for arquivo in uteis + editais:
        caminho = destino / arquivo["nome"]
        if caminho.exists():
            baixados[arquivo["nome"]] = caminho.read_bytes()
            continue
        if arquivo["nome"] in arquivos_ja_processados:
            continue
        try:
            conteudo = coletor.baixar(sessao, slug, arquivo["nome"])
        except Exception as erro:
            print(f"  [SKIP] {arquivo['nome'][:50]}: {erro.__class__.__name__}")
            continue
        caminho.write_bytes(conteudo)
        baixados[arquivo["nome"]] = conteudo
        http_utils.aguardar()

    if not baixados and alvo_itens.exists():
        return len(itens_existentes)

    # Indice por nome em caixa alta: a banca alterna "GAB_DEFINITIVO_" e
    # "Gab_Definitivo_" no mesmo acervo.
    por_nome = {nome.upper(): nome for nome in baixados}

    # Salva mapa isolado de gabaritos em gabarito.json para consulta leve e rápida
    mapa_gabs: dict[str, dict[int, str]] = {}
    for arquivo in uteis:
        if config.classificar(arquivo) == config.GABARITO_DEFINITIVO:
            conteudo_gab = baixados.get(arquivo["nome"])
            if conteudo_gab:
                g = parser.extrair_gabarito(conteudo_gab)
                if g:
                    mapa_gabs[arquivo["nome"]] = g
    if mapa_gabs:
        alvo_gab = pasta_base / slug / "gabarito.json"
        alvo_gab.write_text(json.dumps(mapa_gabs, ensure_ascii=False, indent=1), encoding="utf-8")

    itens: list[dict] = []
    for arquivo in uteis + editais:
        conteudo = baixados.get(arquivo["nome"])
        if conteudo is None:
            continue
        tipo = config.classificar(arquivo)

        if tipo == config.CADERNO_COM_JUSTIFICATIVA:
            extraidos = parser.extrair_itens(conteudo)
        elif tipo == config.CADERNO:
            par = _par_de_gabarito(arquivo["nome"], por_nome)
            gabaritos = parser.extrair_gabarito(baixados[par]) if par else {}
            extraidos = _itens_do_caderno(conteudo, gabaritos)
        else:
            continue  # gabarito sozinho nao vira questao: e meia questao

        for item in extraidos:
            item["concurso"] = slug
            item["arquivo"] = arquivo["nome"]
            itens.append(item)

    if itens:
        alvo = pasta_base / slug / "itens.json"
        alvo.write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")

        # Auto-Purge: se manter_pdfs for False, purga cadernos e gabaritos brutos ja estruturados
        if not manter_pdfs:
            nomes_para_purgar = {
                a["nome"]
                for a in uteis
                if config.classificar(a)
                in (
                    config.GABARITO_DEFINITIVO,
                    config.CADERNO,
                    config.CADERNO_COM_JUSTIFICATIVA,
                )
            }
            for arq_path in destino.iterdir():
                if arq_path.name in nomes_para_purgar:
                    try:
                        arq_path.unlink()
                    except OSError:
                        pass
    return len(itens)


def coletar_todos(slugs: list[str] | None = None, manter_pdfs: bool = False) -> None:
    sessao = http_utils.criar_sessao()
    if slugs is None:
        slugs = [c["slug"] for c in coletor.listar_concursos(sessao)]

    print(f"CEBRASPE — {len(slugs)} concursos a varrer (manter_pdfs={manter_pdfs})")
    total = 0
    for indice, slug in enumerate(slugs, 1):
        try:
            extraidos = coletar_concurso(sessao, slug, PASTA, manter_pdfs=manter_pdfs)
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
    manter = "--manter-pdfs" in sys.argv
    slugs = [arg for arg in sys.argv[1:] if not arg.startswith("--")] or None
    coletar_todos(slugs, manter_pdfs=manter)


if __name__ == "__main__":
    main()
