"""Scraper para certames e provas do IADES utilizando a arquitetura Lean (CLAUDE.md 1.2)."""

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseBancaScraper
from scrapers.iades import parser

BASE_URL = "https://www.iades.com.br/inscricao/"


class IADESScraper(BaseBancaScraper):
    """Implementação do coletor do IADES compatível com o ciclo Process & Purge."""

    nome_banca: str = "IADES"

    def listar_concursos(self) -> list[dict[str, Any]]:
        """Varre os concursos publicados no portal do IADES."""
        url = urljoin(BASE_URL, "?pagina=concursos")
        try:
            resp = self.sessao.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"Erro ao listar concursos IADES: {e}")
            return []

        concursos = []
        # Localiza links para páginas de certames (?pagina=concurso&id=...)
        for link in soup.find_all("a", href=re.compile(r"pagina=concurso&id=(\w+)", re.IGNORECASE)):
            href = link.get("href", "")
            match = re.search(r"id=(\w+)", href)
            if not match:
                continue
            slug = match.group(1)
            nome = " ".join(link.get_text().split())
            if len(nome) > 3 and not any(c["slug"] == slug for c in concursos):
                concursos.append({
                    "slug": slug,
                    "nome": nome,
                    "ano": 2024,
                })
        return concursos

    def listar_arquivos(self, slug: str) -> list[dict[str, Any]]:
        """Lista os arquivos oficiais do concurso pelo ID."""
        url = urljoin(BASE_URL, f"?pagina=concurso&id={slug}")
        try:
            resp = self.sessao.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"Erro ao listar arquivos do certame IADES {slug}: {e}")
            return []

        arquivos = []
        for a in soup.find_all("a", href=re.compile(r"\.pdf", re.IGNORECASE)):
            href = a.get("href", "")
            nome = href.split("/")[-1]
            desc = " ".join(a.get_text().split())
            if nome and not any(arq["nome"] == nome for arq in arquivos):
                arquivos.append({
                    "nome": nome,
                    "url": urljoin(BASE_URL, href),
                    "descricao": desc,
                })
        return arquivos

    def baixar_arquivo(self, slug: str, nome_arquivo: str) -> bytes:
        """Baixa o PDF do concurso."""
        arquivos = self.listar_arquivos(slug)
        url_alvo = None
        for a in arquivos:
            if a["nome"] == nome_arquivo:
                url_alvo = a.get("url")
                break

        if not url_alvo:
            url_alvo = urljoin(BASE_URL, f"upload/{nome_arquivo}")

        resp = self.sessao.get(url_alvo, timeout=30)
        resp.raise_for_status()
        return resp.content

    def classificar_arquivo(self, arquivo: dict[str, Any]) -> str:
        """Identifica caderno de prova, gabarito definitivo ou edital de abertura."""
        alvo = f"{arquivo.get('nome', '')} {arquivo.get('descricao', '')}".upper()

        if "GABARITO" in alvo and ("DEFINITIVO" in alvo or "FINAL" in alvo):
            return "gabarito_definitivo"
        if "CADERNO" in alvo or "PROVA OBJETIVA" in alvo or "PROVA_OBJETIVA" in alvo:
            if "RESULTADO" not in alvo and "CONVOCA" not in alvo:
                return "caderno"
        if "EDITAL" in alvo and ("ABERTURA" in alvo or "NORMATIVO" in alvo):
            if "RESULTADO" not in alvo and "HOMOLOGA" not in alvo:
                return "edital"

        return "outro"

    def extrair_gabarito(self, conteudo_pdf: bytes) -> dict[int, str]:
        return parser.extrair_gabarito(conteudo_pdf)

    def extrair_caderno(self, conteudo_pdf: bytes, gabaritos: dict[int, str]) -> list[dict[str, Any]]:
        return parser.extrair_itens(conteudo_pdf, gabaritos)
