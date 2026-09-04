"""Automação da Cebraspe: fala com a API e a CDN. Camada de automação (CLAUDE.md 1.2).

Só HTTP. Não interpreta PDF — isso é de `parser.py` — e não grava nada — isso é
do orquestrador. A sessão vem injetada, já aberta (CLAUDE.md 2).

A Cebraspe é a fonte mais aberta do ecossistema: `robots.txt` do portal traz
`Disallow:` vazio, a CDN e a API não têm `robots.txt`, e nada exige login ou
cota. Os endpoints abaixo saíram da configuração exposta em texto puro no
bundle React do site (`/concursos/static/js/main.*.chunk.js`, chaves `apiLink`,
`cdnLink` e `eventoURL`).
"""

import urllib.parse

API = "https://apis.cebraspe.org.br/cebraspe"
CDN = "https://cdn.cebraspe.org.br/concursos"

URL_EVENTOS = f"{API}/eventos/tipo/concursos/fase/{{fase}}"
URL_EVENTO = f"{API}/eventos/{{slug}}"
URL_ARQUIVO = f"{CDN}/{{slug}}/arquivos/{{arquivo}}"

# Campos do detalhe do evento que trazem arquivos, e o rótulo de origem de cada.
CAMPOS_DE_ARQUIVO = {"arquivosGabarito": "gabarito", "arquivosEdital": "edital"}


def _tempo(sessao) -> int:
    return getattr(sessao, "timeout", 30)


def listar_concursos(sessao, fase: str = "encerrado") -> list[dict]:
    """Lista os concursos de uma fase (`encerrado`, `andamento`, `novos`).

    Devolve dicts com `slug` (o identificador usado na CDN), `nome` e `ano`.
    """
    resposta = sessao.get(URL_EVENTOS.format(fase=fase), timeout=_tempo(sessao))
    resposta.raise_for_status()
    dados = resposta.json() or []

    concursos = []
    for grupo in dados:
        for evento in grupo.get("eventos") or []:
            slug = evento.get("eventoURL")
            if not slug:
                continue
            concursos.append(
                {
                    "slug": slug,
                    "nome": evento.get("eventoNomeAbreviado") or slug,
                    "ano": evento.get("eventoAno"),
                }
            )
    return concursos


def listar_arquivos(sessao, slug: str) -> list[dict]:
    """Lista os arquivos publicados de um concurso.

    Devolve dicts com `nome`, `descricao` e `origem` (`gabarito` ou `edital`).
    A API entrega o nome exato de cada arquivo, então não há adivinhação: os
    certames recentes usam hashes SHA-256 no nome, que nenhuma enumeração
    acertaria.

    Concurso inexistente devolve lista vazia em vez de estourar — um slug ruim
    não pode derrubar a varredura dos outros 424 (CLAUDE.md 3).
    """
    resposta = sessao.get(URL_EVENTO.format(slug=slug), timeout=_tempo(sessao))
    if resposta.status_code >= 400:
        return []
    dados = resposta.json() or {}

    arquivos = []
    for campo, origem in CAMPOS_DE_ARQUIVO.items():
        for arquivo in dados.get(campo) or []:
            nome = arquivo.get("nomeArquivo")
            if not nome:
                continue
            arquivos.append(
                {
                    "nome": nome,
                    "descricao": arquivo.get("descricaoArquivo") or "",
                    "origem": origem,
                }
            )
    return arquivos


def baixar(sessao, slug: str, nome_arquivo: str) -> bytes:
    """Baixa um arquivo da CDN e devolve os bytes crus.

    O slug vai em minúsculas: é assim que os caminhos existem na CDN, mesmo a
    API devolvendo em maiúsculas (`PC_DF_24_ADM` -> `pc_df_24_adm`).
    """
    url = URL_ARQUIVO.format(
        slug=slug.lower(),
        arquivo=urllib.parse.quote(nome_arquivo),
    )
    resposta = sessao.get(url, timeout=_tempo(sessao))
    resposta.raise_for_status()
    return resposta.content
