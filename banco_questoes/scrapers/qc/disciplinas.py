"""Registro das disciplinas do QConcursos. Config estática, sem I/O.

Antes, `coletar_qc.py` iterava as 8 matérias do `edital.py` — que descreve só
o SEDES/DF. Resultado: os outros 8 concursos de `configuracoes_editais/` não
coletavam uma questão sequer, por mais que estivessem configurados.

Aqui a coleta passa a ser por DISCIPLINA, e o edital vira consumidor: escolhe
o que usar em vez de ditar o que existe. Mesmo papel de `scrapers/pci/config.py`
no coletor do PCI, que já funciona em modo multi-concurso.

Os nomes das 8 originais são preservados letra por letra: são a chave do
progresso em `progresso_scraper` e o valor de `materia` das questões do QC já
gravadas. Renomear rachava os dados em dois.

Uma matéria pode juntar várias disciplinas do QC (o campo aceita repetição de
`discipline_ids[]`), mas um id NUNCA aparece em duas matérias — isso faria a
mesma questão ser gravada com duas classificações.

IDs confirmados na interface logada do QConcursos em 03/09/2026.
"""

import urllib.parse

BASE = "https://www.qconcursos.com/questoes-de-concursos/questoes"

# Descarta questões anuladas e desatualizadas: não servem para estudo.
FILTROS = {"exclude_nullified": "true", "exclude_outdated": "true"}

DISCIPLINAS: dict[str, tuple[int, ...]] = {
    # --- as 8 do SEDES/DF, com os nomes originais preservados ---
    "Língua Portuguesa": (1,),
    "Direito Administrativo": (2,),
    "Direito Constitucional": (3,),
    "Conhecimentos do DF e Legislação": (61,),
    # 188 é "Serviço Social" no QC; o edital do SEDES chama de SUAS. O nome
    # canônico fica para a taxonomia resolver — aqui vale não rachar os dados.
    "SUAS": (188,),
    "Atendimento, Rotinas Administrativas e Arquivologia": (20, 187, 174),
    "Recursos Materiais, Patrimônio e Compras": (213,),
    # O QC não tem disciplina para os programas distritais; ECA e Estatuto da
    # Pessoa Idosa são a base legal mais próxima que existe lá.
    "Programas e Benefícios do DF": (233, 534),
    # --- as que destravam os outros 8 concursos ---
    "Noções de Informática": (46,),  # BACEN, BB, Correios, INSS, PMDF, PRF, RFB
    "Raciocínio Lógico": (4,),  # Correios, INSS, PMDF, PRF
    "Direito Penal": (9,),  # PMDF, PCDF
    "Direito Penal Militar": (203,),  # PMDF — ramo distinto do Direito Penal
    "Direito Processual Penal": (10,),  # PCDF
    "Direito Processual Penal Militar": (204,),  # PMDF
    "Administração Geral": (21,),  # RFB, BB
    "Administração Pública": (26,),  # INSS, PMDF, PRF, RFB
    "Administração Financeira e Orçamentária": (33,),  # BACEN, RFB
    "Análise de Balanços": (235,),  # BACEN, RFB
    "Logística": (409,),  # Correios
    "Algoritmos e Estrutura de Dados": (98,),  # BACEN (TI)
    "Arquitetura de Computadores": (93,),  # BACEN (TI)
    "Arquitetura de Software": (503,),  # BACEN (TI)
}


def url_de_busca(ids: tuple[int, ...]) -> str:
    """Monta a URL de busca do QC para uma ou mais disciplinas."""
    partes = list(FILTROS.items()) + [("discipline_ids[]", str(i)) for i in ids]
    return f"{BASE}?{urllib.parse.urlencode(partes)}"


def listar() -> list[tuple[str, tuple[int, ...]]]:
    """Devolve (matéria, ids) de todas as disciplinas registradas."""
    return list(DISCIPLINAS.items())
