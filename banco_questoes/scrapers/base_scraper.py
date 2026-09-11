"""Classe base unificada para scrapers de bancas de concurso.

Padroniza o ciclo Lean 'Process & Purge':
1. Listagem de certames e arquivos
2. Filtragem estrita (Zero-Lixo: apenas caderno, gabarito definitivo e edital normativo de abertura)
3. Download com controle de taxa e tolerância a falhas
4. Extração estruturada (geração de itens.json e gabarito.json)
5. Auto-Purge: descarte imediato dos PDFs pesados para economizar 98% de espaço em disco
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path
import shutil
from typing import Any

from scrapers import http_utils

MINIMO_LIVRE_GB = 2.0


class DiscoCheio(RuntimeError):
    """Espaço em disco abaixo do mínimo seguro."""


def espaco_livre_gb(caminho: Path) -> float:
    alvo = caminho if caminho.exists() else caminho.parent
    return shutil.disk_usage(alvo).free / 1024**3


class BaseBancaScraper(ABC):
    """Contrato base para coletores de bancas examinadoras."""

    nome_banca: str = "Base"

    def __init__(self, sessao=None) -> None:
        self.sessao = sessao or http_utils.criar_sessao()

    @abstractmethod
    def listar_concursos(self) -> list[dict[str, Any]]:
        """Devolve lista de certames: [{'slug': str, 'nome': str, 'ano': int}, ...]."""
        raise NotImplementedError

    @abstractmethod
    def listar_arquivos(self, slug: str) -> list[dict[str, Any]]:
        """Devolve arquivos publicados: [{'nome': str, 'descricao': str, 'tipo': str}, ...]."""
        raise NotImplementedError

    @abstractmethod
    def baixar_arquivo(self, slug: str, nome_arquivo: str) -> bytes:
        """Baixa o conteúdo cru do arquivo."""
        raise NotImplementedError

    @abstractmethod
    def classificar_arquivo(self, arquivo: dict[str, Any]) -> str:
        """Classifica o arquivo em: 'caderno', 'gabarito_definitivo', 'edital', 'outro'."""
        raise NotImplementedError

    @abstractmethod
    def extrair_gabarito(self, conteudo_pdf: bytes) -> dict[int, str]:
        """Extrai mapeamento {numero_item: resposta} a partir do PDF de gabarito."""
        raise NotImplementedError

    @abstractmethod
    def extrair_caderno(self, conteudo_pdf: bytes, gabaritos: dict[int, str]) -> list[dict[str, Any]]:
        """Extrai enunciados e mescla com gabarito oficial, devolvendo lista de itens."""
        raise NotImplementedError

    def purgar_temporarios(self, destino: Path, arquivos_para_purgar: set[str]) -> int:
        """Exclui arquivos brutos pesados após extração bem-sucedida."""
        purgados = 0
        for arq in destino.iterdir():
            if arq.name in arquivos_para_purgar:
                try:
                    arq.unlink()
                    purgados += 1
                except OSError:
                    pass
        return purgados

    def processar_concurso(self, slug: str, pasta_base: Path, manter_pdfs: bool = False) -> int:
        """Executa a esteira Lean para um concurso."""
        livre = espaco_livre_gb(pasta_base)
        if livre < MINIMO_LIVRE_GB:
            raise DiscoCheio(f"Restam {livre:.1f} GB, menos que o mínimo de {MINIMO_LIVRE_GB} GB")

        arquivos = self.listar_arquivos(slug)
        if not arquivos:
            return 0

        cadernos = []
        gabaritos = []
        editais_abertura = []

        for arq in arquivos:
            tipo = self.classificar_arquivo(arq)
            if tipo == "caderno":
                cadernos.append(arq)
            elif tipo == "gabarito_definitivo":
                gabaritos.append(arq)
            elif tipo == "edital":
                desc = (arq.get("nome", "") + " " + arq.get("descricao", "")).upper()
                if "ABERTURA" in desc or "NORMATIVO" in desc:
                    editais_abertura.append(arq)

        if not cadernos and not gabaritos:
            return 0

        destino = pasta_base / slug / "arquivos"
        destino.mkdir(parents=True, exist_ok=True)

        baixados: dict[str, bytes] = {}
        selecionados = cadernos + gabaritos + editais_abertura[:1]
        for arq in selecionados:
            caminho = destino / arq["nome"]
            if caminho.exists():
                baixados[arq["nome"]] = caminho.read_bytes()
                continue
            try:
                conteudo = self.baixar_arquivo(slug, arq["nome"])
                caminho.write_bytes(conteudo)
                baixados[arq["nome"]] = conteudo
                http_utils.aguardar()
            except Exception as err:
                print(f"  [SKIP] {arq['nome'][:40]}: {err.__class__.__name__}")
                continue

        # Extrai mapa consolidado de gabaritos
        mapa_gabaritos: dict[str, dict[int, str]] = {}
        for arq in gabaritos:
            conteudo_gab = baixados.get(arq["nome"])
            if conteudo_gab:
                g = self.extrair_gabarito(conteudo_gab)
                if g:
                    mapa_gabaritos[arq["nome"]] = g

        if mapa_gabaritos:
            alvo_gab = pasta_base / slug / "gabarito.json"
            alvo_gab.write_text(json.dumps(mapa_gabaritos, ensure_ascii=False, indent=1), encoding="utf-8")

        # Extrai itens dos cadernos
        todos_itens: list[dict[str, Any]] = []
        gabarito_unificado = {}
        for g in mapa_gabaritos.values():
            gabarito_unificado.update(g)

        for arq in cadernos:
            conteudo_cad = baixados.get(arq["nome"])
            if not conteudo_cad:
                continue
            itens = self.extrair_caderno(conteudo_cad, gabarito_unificado)
            for it in itens:
                it["concurso"] = slug
                it["banca"] = self.nome_banca
                it["arquivo"] = arq["nome"]
                todos_itens.append(it)

        if todos_itens:
            alvo_itens = pasta_base / slug / "itens.json"
            alvo_itens.write_text(json.dumps(todos_itens, ensure_ascii=False, indent=1), encoding="utf-8")

            # Auto-purge dos PDFs de caderno e gabarito
            if not manter_pdfs:
                purgar = {a["nome"] for a in cadernos + gabaritos}
                self.purgar_temporarios(destino, purgar)

        return len(todos_itens)
