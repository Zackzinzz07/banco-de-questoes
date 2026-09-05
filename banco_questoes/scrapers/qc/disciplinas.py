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

from scrapers.qc.catalogo import CATALOGO

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


# Disciplinas que existem no registro mas NAO devem ser coletadas, com o
# motivo. O QC organiza o acervo em tres niveis -- discipline_ids[] (a
# disciplina), subject_ids[] (o assunto) e institute_ids[] (o orgao) -- e este
# registro so usa o primeiro. Quando a disciplina sozinha e larga demais, o
# resultado nao e "menos preciso": e conteudo de outro concurso entrando com o
# rotulo errado.
PAUSADAS: dict[str, str] = {
    "Conhecimentos do DF e Legislação": (
        "o id 61 e 'Legislacao Estadual' generico, nao legislacao do DF. Das "
        "1.546 questoes ja coletadas sob esse rotulo, so 25 (2%) eram de orgao "
        "do DF -- o resto veio de SEDUC-SP, Policia Penal-RS, AL-CE, MPE-GO. "
        "Filtrar a legislacao distrital exige subject_ids[] (LODF, LC 840/2011, "
        "Lei 4.990/2012), que ainda nao temos."
    ),
    "Programas e Benefícios do DF": (
        "ECA (233) e Estatuto da Pessoa Idosa (534) foram aproximacao minha, "
        "nao equivalencia. O mapeamento das bancas mostra que os programas "
        "distritais sao subdivisoes de Servico Social (188) indexadas por "
        "institute_ids[] da SEDES -- outro nivel da taxonomia."
    ),
}


# O catálogo do QC entra depois das matérias definidas acima, e só onde não
# colide: id já usado numa matéria anterior não é reaproveitado, senão a mesma
# questão seria coletada com duas classificações. Por isso Arquivologia (20)
# não ganha entrada própria — ela já vive dentro da composta do SEDES.
_ids_em_uso = {identificador for ids in DISCIPLINAS.values() for identificador in ids}
for _nome, _id in CATALOGO.items():
    if _id not in _ids_em_uso and _nome not in DISCIPLINAS:
        DISCIPLINAS[_nome] = (_id,)
        _ids_em_uso.add(_id)


def url_de_busca(ids: tuple[int, ...]) -> str:
    """Monta a URL de busca do QC para uma ou mais disciplinas."""
    partes = list(FILTROS.items()) + [("discipline_ids[]", str(i)) for i in ids]
    return f"{BASE}?{urllib.parse.urlencode(partes)}"


def listar() -> list[tuple[str, tuple[int, ...]]]:
    """Devolve (matéria, ids) das disciplinas ATIVAS.

    As pausadas continuam em DISCIPLINAS — some da coleta, não do registro,
    para não perder o id nem o histórico de por que saiu.
    """
    return [(nome, ids) for nome, ids in DISCIPLINAS.items() if nome not in PAUSADAS]
