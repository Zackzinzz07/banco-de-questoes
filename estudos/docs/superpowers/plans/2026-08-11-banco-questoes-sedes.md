# Banco de Questões SEDES/DF — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Banco SQLite local de questões (QConcursos + provas PDF da Quadrix) com geradores de simulado em PDF por matéria, conforme o design `estudos/docs/superpowers/specs/2026-08-11-banco-questoes-sedes-design.md`.

**Architecture:** Pasta nova `banco_questoes/` na raiz de `training/` (separada do Django). Módulos planos: `db.py` (SQLite + dedupe), `edital.py` (matérias canônicas), `coletor_quadrix.py` (requests + pdfplumber), `scraper_qc.py` (Selenium no Chrome logado), `simulados/` (ReportLab). Testes com pytest e fixtures locais (sem rede).

**Tech Stack:** Python 3.14 (venv em `training/.venv`), sqlite3 (stdlib), requests, pdfplumber, beautifulsoup4, playwright (trocou o selenium em 11/08 — Chrome v151 bloqueia automação no perfil padrão), reportlab, pytest.

## Global Constraints

- Raiz do código: `c:\Users\Felps\Documents\training\banco_questoes\` — **separado** do projeto Django `estudos/`.
- Python do venv: `..\.venv\Scripts\python.exe` (rodar comandos a partir de `banco_questoes\`).
- Banco: arquivo `banco_de_questoes.db` na pasta `banco_questoes/` (nunca versionar no git).
- Nomes canônicos das 8 matérias (campo `materia`) exatamente como definidos em `edital.py` (Task 3).
- Alternativas armazenadas como JSON `{"A": "...", ...}`; Certo/Errado usa `{"C": "Certo", "E": "Errado"}`.
- `fonte` só aceita `"qconcursos"` ou `"quadrix_pdf"`.
- Nenhuma senha no código (login do QC via perfil do Chrome do usuário).
- Sem comentários por IA; comentário só quando visível no QC.
- Mensagens de erro claras em PT-BR; nunca traceback cru para falha de rede/site.
- Ritmo educado no scraper: pausas de 3–6 s entre páginas.
- **Várias bancas:** a busca no QC filtra só por disciplina/assunto, **sem
  filtro de banca** — questões de qualquer banca com conteúdo do edital entram
  no banco, e o campo `banca` registra a origem de cada uma.
- O usuário é iniciante em Python: código simples, sem classes desnecessárias, comentários curtos em PT-BR.

**Nota de simplificação (desvio consciente do design):** a listagem automática de concursos no site da Quadrix foi trocada por uma lista `PROVAS` curada manualmente no topo de `coletor_quadrix.py` (mesma finalidade — selecionar provas de nível médio com matérias em comum — com muito menos fragilidade de scraping). Preenchê-la é um passo da Task 6.

---

### Task 1: Setup do projeto + `db.py` (schema, salvar com dedupe)

**Files:**
- Create: `c:\Users\Felps\Documents\training\.gitignore`
- Create: `banco_questoes\db.py`
- Create: `banco_questoes\conftest.py` (vazio; faz o pytest achar os módulos)
- Test: `banco_questoes\tests\test_db.py`

**Interfaces:**
- Produces: `conectar(caminho=None) -> sqlite3.Connection` (cria tabelas se não existirem, `row_factory=sqlite3.Row`); `salvar_questao(con, questao: dict) -> bool` (True inseriu, False duplicada); `hash_enunciado(texto: str) -> str`; `normalizar_enunciado(texto: str) -> str`. Dict de questão usa as chaves: `id_qc, enunciado, alternativas (dict), gabarito, comentario, materia, assunto, banca, orgao, ano, prova, fonte`.

- [ ] **Step 1: Inicializar git e estrutura**

```powershell
cd c:\Users\Felps\Documents\training
git init
New-Item -ItemType Directory -Force banco_questoes\tests, banco_questoes\simulados, banco_questoes\provas_pdf
New-Item -ItemType File banco_questoes\conftest.py
```

Criar `training\.gitignore`:

```
.venv/
__pycache__/
*.pyc
banco_questoes/banco_de_questoes.db
banco_questoes/provas_pdf/
banco_questoes/relatorio_extracao.txt
banco_questoes/simulados/*.pdf
estudos/estudos/db.sqlite3
```

- [ ] **Step 2: Instalar dependências**

```powershell
..\.venv\Scripts\python.exe -m pip install requests beautifulsoup4 pdfplumber selenium reportlab pytest
```

(Rodar de `banco_questoes\`. reportlab talvez já esteja instalado — sem problema.)

- [ ] **Step 3: Escrever os testes que falham** — `banco_questoes\tests\test_db.py`:

```python
import db


def questao_exemplo(**extras):
    q = {
        "id_qc": "Q1234567",
        "enunciado": "Qual é a capital do Brasil?",
        "alternativas": {"A": "Brasília", "B": "Goiânia", "C": "Rio", "D": "SP", "E": "BH"},
        "gabarito": "A",
        "comentario": None,
        "materia": "Língua Portuguesa",
        "assunto": "Interpretação de textos",
        "banca": "Instituto Quadrix",
        "orgao": "SEDES/DF",
        "ano": 2026,
        "prova": "Técnico Administrativo",
        "fonte": "qconcursos",
    }
    q.update(extras)
    return q


def test_salvar_e_ler(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    assert db.salvar_questao(con, questao_exemplo()) is True
    linha = con.execute("SELECT * FROM questoes").fetchone()
    assert linha["id_qc"] == "Q1234567"
    assert linha["materia"] == "Língua Portuguesa"
    assert linha["usada_em_simulado"] == 0


def test_dedupe_por_id_qc(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_questao(con, questao_exemplo())
    assert db.salvar_questao(con, questao_exemplo(enunciado="Outro texto")) is False


def test_dedupe_por_hash_enunciado(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_questao(con, questao_exemplo())
    repetida = questao_exemplo(id_qc=None, enunciado="  qual  é a CAPITAL do Brasil? ")
    assert db.salvar_questao(con, repetida) is False


def test_duas_questoes_sem_id_qc_nao_conflitam(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    assert db.salvar_questao(con, questao_exemplo(id_qc=None)) is True
    assert db.salvar_questao(con, questao_exemplo(id_qc=None, enunciado="Texto diferente.")) is True


def test_normalizar_enunciado():
    assert db.normalizar_enunciado("  Olá   MUNDO \n ") == "olá mundo"
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_db.py -v`
Expected: FAIL / erro de import (`db` não existe).

- [ ] **Step 5: Implementar `banco_questoes\db.py`**

```python
"""Banco SQLite de questões: conexão, criação de tabelas, salvar com dedupe."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ARQUIVO_BANCO = Path(__file__).resolve().parent / "banco_de_questoes.db"

SQL_CRIAR = """
CREATE TABLE IF NOT EXISTS questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_qc TEXT UNIQUE,
    enunciado TEXT NOT NULL,
    hash_enunciado TEXT UNIQUE NOT NULL,
    alternativas TEXT NOT NULL,
    gabarito TEXT,
    comentario TEXT,
    materia TEXT NOT NULL,
    assunto TEXT,
    banca TEXT,
    orgao TEXT,
    ano INTEGER,
    prova TEXT,
    fonte TEXT NOT NULL,
    usada_em_simulado INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS progresso_scraper (
    materia TEXT PRIMARY KEY,
    ultima_pagina INTEGER NOT NULL
);
"""


def conectar(caminho=None):
    con = sqlite3.connect(caminho or ARQUIVO_BANCO)
    con.row_factory = sqlite3.Row
    con.executescript(SQL_CRIAR)
    return con


def normalizar_enunciado(texto):
    return re.sub(r"\s+", " ", texto).strip().lower()


def hash_enunciado(texto):
    return hashlib.sha256(normalizar_enunciado(texto).encode("utf-8")).hexdigest()


def salvar_questao(con, q):
    """Insere a questão; retorna True se inseriu, False se já existia (dedupe)."""
    try:
        con.execute(
            "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, alternativas,"
            " gabarito, comentario, materia, assunto, banca, orgao, ano, prova, fonte)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                q.get("id_qc"),
                q["enunciado"],
                hash_enunciado(q["enunciado"]),
                json.dumps(q["alternativas"], ensure_ascii=False),
                q.get("gabarito"),
                q.get("comentario"),
                q["materia"],
                q.get("assunto"),
                q.get("banca"),
                q.get("orgao"),
                q.get("ano"),
                q.get("prova"),
                q["fonte"],
            ),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
```

(Colunas `id_qc` e `hash_enunciado` com UNIQUE são as duas travas de dedupe; UNIQUE em SQLite permite vários NULL em `id_qc`.)

- [ ] **Step 6: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_db.py -v`
Expected: 5 PASS

- [ ] **Step 7: Commit**

```powershell
cd c:\Users\Felps\Documents\training
git add .gitignore banco_questoes
git commit -m "feat: banco_questoes - schema SQLite e dedupe de questoes"
```

---

### Task 2: `db.py` — sorteio, marcação de usadas, progresso e gabaritos pendentes

**Files:**
- Modify: `banco_questoes\db.py` (acrescentar funções ao final)
- Test: `banco_questoes\tests\test_db.py` (acrescentar testes)

**Interfaces:**
- Consumes: `conectar`, `salvar_questao` (Task 1).
- Produces: `sortear_questoes(con, materia, quantidade) -> list[dict]` (alternativas já como dict; completa com repetidas se faltar, avisando via print); `marcar_usadas(con, ids: list[int])`; `zerar_usadas(con)`; `obter_progresso(con, materia) -> int` (0 se nunca); `salvar_progresso(con, materia, pagina)`; `sem_gabarito(con) -> list[dict]` (só questões com `id_qc` e `gabarito IS NULL`); `atualizar_gabarito(con, id_qc, gabarito, comentario=None)`.

- [ ] **Step 1: Acrescentar testes em `tests\test_db.py`**

```python
def test_sorteio_sem_repeticao(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    for i in range(5):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    sorteadas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    assert len(sorteadas) == 3
    assert isinstance(sorteadas[0]["alternativas"], dict)
    db.marcar_usadas(con, [q["id"] for q in sorteadas])
    restantes = db.sortear_questoes(con, "Língua Portuguesa", 2)
    ids_novos = {q["id"] for q in restantes}
    assert ids_novos.isdisjoint({q["id"] for q in sorteadas})


def test_sorteio_completa_com_repetidas(tmp_path, capsys):
    con = db.conectar(tmp_path / "t.db")
    for i in range(3):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    todas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    db.marcar_usadas(con, [q["id"] for q in todas])
    de_novo = db.sortear_questoes(con, "Língua Portuguesa", 2)
    assert len(de_novo) == 2
    assert "repetidas" in capsys.readouterr().out


def test_zerar_usadas(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_questao(con, questao_exemplo())
    q = db.sortear_questoes(con, "Língua Portuguesa", 1)
    db.marcar_usadas(con, [q[0]["id"]])
    db.zerar_usadas(con)
    assert con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"] == 0


def test_progresso(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    assert db.obter_progresso(con, "Direito Administrativo") == 0
    db.salvar_progresso(con, "Direito Administrativo", 7)
    db.salvar_progresso(con, "Direito Administrativo", 8)
    assert db.obter_progresso(con, "Direito Administrativo") == 8


def test_sem_gabarito_e_atualizar(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_questao(con, questao_exemplo(id_qc="Q1", gabarito=None, enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="Q2", gabarito="B", enunciado="Dois?"))
    db.salvar_questao(con, questao_exemplo(id_qc=None, gabarito=None, enunciado="Três?"))
    pendentes = db.sem_gabarito(con)
    assert [p["id_qc"] for p in pendentes] == ["Q1"]
    db.atualizar_gabarito(con, "Q1", "C", "Comentário do professor.")
    linha = con.execute("SELECT gabarito, comentario FROM questoes WHERE id_qc='Q1'").fetchone()
    assert (linha["gabarito"], linha["comentario"]) == ("C", "Comentário do professor.")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_db.py -v`
Expected: os 5 testes novos FAIL (`AttributeError: module 'db' has no attribute ...`).

- [ ] **Step 3: Implementar (acrescentar ao final de `db.py`)**

```python
def sortear_questoes(con, materia, quantidade):
    """Sorteia questões não usadas; se faltar, avisa e completa com repetidas."""
    linhas = con.execute(
        "SELECT * FROM questoes WHERE materia=? AND usada_em_simulado=0"
        " ORDER BY RANDOM() LIMIT ?", (materia, quantidade)).fetchall()
    questoes = [dict(l) for l in linhas]
    faltam = quantidade - len(questoes)
    if faltam > 0:
        repetidas = con.execute(
            "SELECT * FROM questoes WHERE materia=? AND usada_em_simulado=1"
            " ORDER BY RANDOM() LIMIT ?", (materia, faltam)).fetchall()
        if repetidas:
            print(f"Aviso: só {len(questoes)} questões inéditas de {materia};"
                  f" completando com {len(repetidas)} repetidas.")
        questoes += [dict(l) for l in repetidas]
    for q in questoes:
        q["alternativas"] = json.loads(q["alternativas"])
    return questoes


def marcar_usadas(con, ids):
    con.executemany("UPDATE questoes SET usada_em_simulado=1 WHERE id=?",
                    [(i,) for i in ids])
    con.commit()


def zerar_usadas(con):
    con.execute("UPDATE questoes SET usada_em_simulado=0")
    con.commit()


def obter_progresso(con, materia):
    linha = con.execute("SELECT ultima_pagina FROM progresso_scraper WHERE materia=?",
                        (materia,)).fetchone()
    return linha["ultima_pagina"] if linha else 0


def salvar_progresso(con, materia, pagina):
    con.execute(
        "INSERT INTO progresso_scraper (materia, ultima_pagina) VALUES (?,?)"
        " ON CONFLICT(materia) DO UPDATE SET ultima_pagina=excluded.ultima_pagina",
        (materia, pagina))
    con.commit()


def sem_gabarito(con):
    linhas = con.execute(
        "SELECT * FROM questoes WHERE gabarito IS NULL AND id_qc IS NOT NULL").fetchall()
    return [dict(l) for l in linhas]


def atualizar_gabarito(con, id_qc, gabarito, comentario=None):
    con.execute("UPDATE questoes SET gabarito=?, comentario=? WHERE id_qc=?",
                (gabarito, comentario, id_qc))
    con.commit()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_db.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```powershell
git add banco_questoes
git commit -m "feat: sorteio sem repeticao, progresso do scraper e gabaritos pendentes"
```

---

### Task 3: `edital.py` — matérias canônicas do Edital nº 1/2026

**Files:**
- Create: `banco_questoes\edital.py`
- Test: `banco_questoes\tests\test_edital.py`

**Interfaces:**
- Produces: `MATERIAS: dict[str, dict]` — chave = nome canônico; valor com `"assuntos": list[str]`, `"titulos_pdf": list[str]` (como a matéria aparece em cabeçalhos de prova, MAIÚSCULAS), `"url_qc": str` (URL de busca filtrada no QC; preenchida na Task 8). `nomes_materias() -> list[str]`; `materia_por_titulo(titulo: str) -> str | None`.

- [ ] **Step 1: Escrever teste** — `banco_questoes\tests\test_edital.py`:

```python
import edital


def test_oito_materias_canonicas():
    assert edital.nomes_materias() == [
        "Língua Portuguesa",
        "Conhecimentos do DF e Legislação",
        "SUAS",
        "Programas e Benefícios do DF",
        "Direito Constitucional",
        "Direito Administrativo",
        "Atendimento, Rotinas Administrativas e Arquivologia",
        "Recursos Materiais, Patrimônio e Compras",
    ]


def test_toda_materia_tem_assuntos_e_titulos():
    for nome, dados in edital.MATERIAS.items():
        assert dados["assuntos"], nome
        assert dados["titulos_pdf"], nome
        assert "url_qc" in dados, nome


def test_materia_por_titulo():
    assert edital.materia_por_titulo("LÍNGUA PORTUGUESA") == "Língua Portuguesa"
    assert edital.materia_por_titulo("  Língua  Portuguesa ") == "Língua Portuguesa"
    assert edital.materia_por_titulo("NOÇÕES DE DIREITO ADMINISTRATIVO") == "Direito Administrativo"
    assert edital.materia_por_titulo("MATEMÁTICA") is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_edital.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar `banco_questoes\edital.py`**

```python
"""Matérias e assuntos do Edital nº 1/2026 SEDES/DF (cargo 202, itens 20.2.2/20.2.3)."""

MATERIAS = {
    "Língua Portuguesa": {
        "assuntos": [
            "Compreensão e interpretação de textos",
            "Gêneros e tipos textuais",
            "Ortografia oficial",
            "Coesão e coerência",
            "Morfossintaxe",
            "Pontuação",
            "Concordância verbal e nominal",
            "Regência verbal e nominal",
            "Crase",
            "Substituição e reescrita de trechos",
        ],
        "titulos_pdf": ["LÍNGUA PORTUGUESA", "PORTUGUÊS"],
        "url_qc": "",
    },
    "Conhecimentos do DF e Legislação": {
        "assuntos": [
            "DF e RIDE (LC nº 94/1998)",
            "Plano Diretor de Ordenamento Territorial (PDOT/PDPM)",
            "Lei Orgânica do DF (Título VI)",
            "LC nº 840/2011 (Títulos I, V, VI e VII)",
            "Lei Maria da Penha (Lei nº 11.340/2006)",
            "Lei Distrital nº 7.484/2024",
            "Noções de primeiros socorros",
        ],
        "titulos_pdf": ["CONHECIMENTOS SOBRE O DISTRITO FEDERAL", "REALIDADE DO DF",
                        "CONHECIMENTOS GERAIS DO DF", "LEGISLAÇÃO APLICADA"],
        "url_qc": "",
    },
    "SUAS": {
        "assuntos": [
            "PNAS/2004",
            "SUAS: princípios e seguranças socioassistenciais",
            "NOB/SUAS 2012",
        ],
        "titulos_pdf": ["SUAS", "ASSISTÊNCIA SOCIAL", "POLÍTICA NACIONAL DE ASSISTÊNCIA SOCIAL"],
        "url_qc": "",
    },
    "Programas e Benefícios do DF": {
        "assuntos": [
            "Cartão Prato Cheio (Lei nº 7.009/2021)",
            "Cartão Gás (Lei nº 6.938/2021)",
            "Plano DF Social (Lei nº 7.008/2021)",
            "Benefícios Eventuais (Lei nº 5.165/2013)",
            "SISAN e Restaurantes Comunitários (Decreto nº 33.329/2011)",
        ],
        "titulos_pdf": ["PROGRAMAS E BENEFÍCIOS", "PROGRAMAS SOCIAIS DO DF"],
        "url_qc": "",
    },
    "Direito Constitucional": {
        "assuntos": [
            "Princípios fundamentais",
            "Direitos e garantias fundamentais",
            "Organização do Estado",
            "Organização da Administração",
            "Servidores públicos",
        ],
        "titulos_pdf": ["DIREITO CONSTITUCIONAL", "NOÇÕES DE DIREITO CONSTITUCIONAL"],
        "url_qc": "",
    },
    "Direito Administrativo": {
        "assuntos": [
            "Estado, governo e administração pública",
            "Ato administrativo",
            "Poderes administrativos",
            "LC nº 840/2011: provimento, vacância e processo disciplinar",
        ],
        "titulos_pdf": ["DIREITO ADMINISTRATIVO", "NOÇÕES DE DIREITO ADMINISTRATIVO"],
        "url_qc": "",
    },
    "Atendimento, Rotinas Administrativas e Arquivologia": {
        "assuntos": [
            "Qualidade no atendimento ao público",
            "Redação oficial",
            "Rotinas administrativas e protocolo",
            "Métodos de arquivamento",
            "Digitalização e gestão de documentos",
        ],
        "titulos_pdf": ["ARQUIVOLOGIA", "ROTINAS ADMINISTRATIVAS", "ATENDIMENTO AO PÚBLICO",
                        "NOÇÕES DE ARQUIVOLOGIA"],
        "url_qc": "",
    },
    "Recursos Materiais, Patrimônio e Compras": {
        "assuntos": [
            "Gestão de estoques",
            "Armazenagem e movimentação de materiais",
            "Gestão patrimonial: tombamento, inventário e baixa",
            "Lei nº 14.133/2021 (licitações e contratos)",
        ],
        "titulos_pdf": ["RECURSOS MATERIAIS", "ADMINISTRAÇÃO DE MATERIAL", "LICITAÇ"],
        "url_qc": "",
    },
}


def nomes_materias():
    return list(MATERIAS)


def materia_por_titulo(titulo):
    """Casa um cabeçalho de seção de prova com a matéria canônica (ou None)."""
    t = " ".join(titulo.split()).upper()
    for nome, dados in MATERIAS.items():
        for padrao in dados["titulos_pdf"]:
            if padrao in t:
                return nome
    return None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_edital.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```powershell
git add banco_questoes
git commit -m "feat: edital.py com as 8 materias canonicas do cargo 202"
```

---

### Task 4: `simulados/` — motor de PDF + scripts por matéria + zerar

**Files:**
- Create: `banco_questoes\simulados\__init__.py` (vazio)
- Create: `banco_questoes\simulados\gerar_simulado.py`
- Create: `banco_questoes\simulados\questoes_portugues.py` (+ 1 por matéria, Step 6)
- Create: `banco_questoes\simulados\zerar_usadas.py`
- Test: `banco_questoes\tests\test_gerar_simulado.py`

**Interfaces:**
- Consumes: `db.conectar`, `db.sortear_questoes`, `db.marcar_usadas`, `db.zerar_usadas` (Tasks 1–2).
- Produces: `gerar(materia: str, quantidade: int, arquivo_saida=None, con=None) -> Path | None` — gera o PDF (capa + questões numeradas + seção "GABARITO COMENTADO"), marca usadas, retorna o caminho (None se banco vazio). `con` injetável para teste.

- [ ] **Step 1: Escrever teste** — `banco_questoes\tests\test_gerar_simulado.py`:

```python
import db
from simulados import gerar_simulado


def questao_fake(i):
    return {
        "id_qc": f"Q{i}",
        "enunciado": f"Enunciado de teste número {i}: assinale a alternativa correta. Texto com < & > para escapar.",
        "alternativas": {"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D", "E": "Opção E"},
        "gabarito": "B" if i % 2 else None,
        "comentario": "Comentário da questão." if i == 1 else None,
        "materia": "Língua Portuguesa",
        "assunto": None, "banca": "Instituto Quadrix", "orgao": "SEDES/DF",
        "ano": 2026, "prova": None, "fonte": "qconcursos",
    }


def test_gera_pdf_e_marca_usadas(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    for i in range(3):
        db.salvar_questao(con, questao_fake(i))
    saida = tmp_path / "simulado.pdf"
    caminho = gerar_simulado.gerar("Língua Portuguesa", 3, saida, con=con)
    assert caminho == saida
    assert saida.exists() and saida.stat().st_size > 1000
    assert saida.read_bytes()[:5] == b"%PDF-"
    usadas = con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"]
    assert usadas == 3


def test_banco_vazio_retorna_none(tmp_path, capsys):
    con = db.conectar(tmp_path / "t.db")
    assert gerar_simulado.gerar("SUAS", 5, tmp_path / "x.pdf", con=con) is None
    assert "Nenhuma questão" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_gerar_simulado.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar `banco_questoes\simulados\gerar_simulado.py`**

```python
"""Motor de simulados em PDF: capa, questões numeradas e gabarito comentado."""
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import db

AZUL = colors.HexColor("#1B3A6B")
CINZA = colors.HexColor("#5A6A85")
PRETO = colors.HexColor("#1E293B")
W, H = A4

_base = getSampleStyleSheet()["Normal"]


def _estilo(nome, **kw):
    padrao = dict(parent=_base, fontSize=10, leading=14, textColor=PRETO)
    padrao.update(kw)
    return ParagraphStyle(nome, **padrao)


e_titulo = _estilo("Titulo", fontSize=20, leading=26, alignment=TA_CENTER,
                   textColor=colors.white, fontName="Helvetica-Bold")
e_sub = _estilo("Sub", fontSize=11, alignment=TA_CENTER,
                textColor=colors.HexColor("#CBD5E1"))
e_num = _estilo("Num", fontName="Helvetica-Bold", textColor=AZUL, fontSize=11,
                spaceBefore=10)
e_origem = _estilo("Origem", fontSize=8, textColor=CINZA)
e_enunciado = _estilo("Enunciado", alignment=TA_JUSTIFY, spaceAfter=4)
e_alt = _estilo("Alt", leftIndent=0.6 * cm)
e_gab = _estilo("Gab", fontSize=9.5, leading=13, spaceAfter=4)


def _capa(materia, quantidade):
    t = Table(
        [[Paragraph("SIMULADO — SEDES/DF", e_titulo)],
         [Paragraph(escape(materia).upper(), e_titulo)],
         [Spacer(1, 0.3 * cm)],
         [Paragraph(f"{quantidade} questões · Gerado em {date.today():%d/%m/%Y}"
                    " · Banca de referência: Instituto Quadrix", e_sub)]],
        colWidths=[W - 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return t


def _origem(q):
    partes = [q.get("banca"), q.get("orgao"), str(q["ano"]) if q.get("ano") else None,
              q.get("assunto")]
    return " · ".join(p for p in partes if p)


def gerar(materia, quantidade, arquivo_saida=None, con=None):
    """Sorteia questões, gera o PDF e marca as usadas. Retorna o caminho ou None."""
    con_proprio = con is None
    if con_proprio:
        con = db.conectar()
    questoes = db.sortear_questoes(con, materia, quantidade)
    if not questoes:
        print(f"Nenhuma questão de '{materia}' no banco. Rode os coletores primeiro.")
        if con_proprio:
            con.close()
        return None

    if arquivo_saida is None:
        nome = materia.lower().replace(" ", "_").replace(",", "")
        arquivo_saida = Path(__file__).resolve().parent / f"simulado_{nome}_{date.today():%Y%m%d}.pdf"
    arquivo_saida = Path(arquivo_saida)

    doc = SimpleDocTemplate(str(arquivo_saida), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Simulado — {materia}")
    story = [_capa(materia, len(questoes)), Spacer(1, 0.8 * cm)]

    for i, q in enumerate(questoes, 1):
        story.append(Paragraph(f"QUESTÃO {i}", e_num))
        origem = _origem(q)
        if origem:
            story.append(Paragraph(escape(origem), e_origem))
        story.append(Paragraph(escape(q["enunciado"]), e_enunciado))
        for letra in sorted(q["alternativas"]):
            story.append(Paragraph(f"({letra}) {escape(q['alternativas'][letra])}", e_alt))

    story.append(PageBreak())
    story.append(Paragraph("GABARITO COMENTADO", e_num))
    story.append(Spacer(1, 0.2 * cm))
    for i, q in enumerate(questoes, 1):
        letra = q["gabarito"] or "— (gabarito ainda não coletado)"
        linha = f"<b>{i}. {escape(letra)}</b>"
        if q.get("comentario"):
            linha += f" — {escape(q['comentario'])}"
        story.append(Paragraph(linha, e_gab))

    doc.build(story)
    db.marcar_usadas(con, [q["id"] for q in questoes])
    print(f"Simulado gerado: {arquivo_saida} ({len(questoes)} questões)")
    if con_proprio:
        con.close()
    return arquivo_saida
```

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_gerar_simulado.py -v`
Expected: 2 PASS

- [ ] **Step 5: Abrir um PDF de fumaça e conferir no olho**

```powershell
..\.venv\Scripts\python.exe -c "import db; from simulados import gerar_simulado as g; con=db.conectar('teste_visual.db'); [db.salvar_questao(con, {'id_qc': f'QV{i}', 'enunciado': f'Enunciado visual {i}?', 'alternativas': {'A':'a','B':'b','C':'c','D':'d','E':'e'}, 'gabarito':'A', 'comentario':'Porque sim.', 'materia':'SUAS', 'fonte':'qconcursos'}) for i in range(5)]; g.gerar('SUAS', 5, 'teste_visual.pdf', con=con)"
Invoke-Item teste_visual.pdf
```

Conferir: capa azul, questões numeradas com alternativas, seção final de gabarito. Comparar com `estudos\simulado-sedes-tdas-tecnico-administrativo.pdf`. Depois apagar `teste_visual.db` e `teste_visual.pdf`.

- [ ] **Step 6: Criar os scripts por matéria e o zerar**

`banco_questoes\simulados\questoes_portugues.py`:

```python
"""Gera um simulado de Língua Portuguesa. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_portugues"""
from simulados import gerar_simulado

MATERIA = "Língua Portuguesa"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
```

Criar os outros 7, mudando nome do arquivo, `MATERIA` e docstring (QUANTIDADE 20 em todos):

| arquivo | MATERIA |
|---|---|
| `questoes_df_legislacao.py` | `Conhecimentos do DF e Legislação` |
| `questoes_suas.py` | `SUAS` |
| `questoes_programas_df.py` | `Programas e Benefícios do DF` |
| `questoes_constitucional.py` | `Direito Constitucional` |
| `questoes_administrativo.py` | `Direito Administrativo` |
| `questoes_atendimento_arquivologia.py` | `Atendimento, Rotinas Administrativas e Arquivologia` |
| `questoes_recursos_materiais.py` | `Recursos Materiais, Patrimônio e Compras` |

`banco_questoes\simulados\zerar_usadas.py`:

```python
"""Zera a marca de 'usada em simulado' de todas as questões (recicla o banco)."""
import db

con = db.conectar()
db.zerar_usadas(con)
print("Pronto: todas as questões voltaram a ficar disponíveis para sorteio.")
con.close()
```

Verificar que rodam sem quebrar (banco vazio → mensagem amigável):

```powershell
..\.venv\Scripts\python.exe -m simulados.questoes_portugues
..\.venv\Scripts\python.exe -m simulados.zerar_usadas
```

Expected: "Nenhuma questão de 'Língua Portuguesa' no banco..." e "Pronto: ...".

- [ ] **Step 7: Commit**

```powershell
git add banco_questoes
git commit -m "feat: motor de simulados em PDF + scripts por materia"
```

---

### Task 5: `coletor_quadrix.py` — parsers de texto (questões, seções, gabarito)

**Files:**
- Create: `banco_questoes\coletor_quadrix.py`
- Test: `banco_questoes\tests\test_coletor_quadrix.py`

**Interfaces:**
- Consumes: `edital.materia_por_titulo` (Task 3).
- Produces: `extrair_questoes_do_texto(texto: str) -> tuple[list[dict], list[int]]` — cada dict: `numero:int, enunciado:str, alternativas:dict, materia:str|None`; segunda lista = números pulados. `extrair_gabarito_de_tabelas(tabelas) -> dict[int, str]`; `casar_gabarito(questoes, gabarito: dict) -> None` (preenche `q["gabarito"]` in-place, None se ausente).

- [ ] **Step 1: Escrever testes** — `banco_questoes\tests\test_coletor_quadrix.py`:

```python
import coletor_quadrix as cq

TEXTO_PROVA = """
CONHECIMENTOS BÁSICOS
LÍNGUA PORTUGUESA

QUESTÃO 1
Assinale a alternativa correta quanto à crase.
(A) Fui à feira.
(B) Fui a feira.
(C) Fui à feiras.
(D) Fui a à feira.
(E) Nenhuma.

QUESTÃO 2
Enunciado sem alternativas legíveis para o parser.

NOÇÕES DE DIREITO ADMINISTRATIVO

QUESTÃO 3
Sobre atos administrativos, julgue os itens e assinale
a alternativa correta.
(A) Item um.
(B) Item dois.
(C) Item três.
(D) Item quatro.
(E) Item cinco.
"""


def test_extrai_questoes_com_materia():
    questoes, puladas = cq.extrair_questoes_do_texto(TEXTO_PROVA)
    assert [q["numero"] for q in questoes] == [1, 3]
    assert puladas == [2]
    assert questoes[0]["materia"] == "Língua Portuguesa"
    assert questoes[1]["materia"] == "Direito Administrativo"
    assert questoes[0]["alternativas"]["A"] == "Fui à feira."
    assert len(questoes[1]["alternativas"]) == 5
    assert "julgue os itens e assinale a alternativa" in questoes[1]["enunciado"]


def test_gabarito_de_tabelas():
    tabelas = [
        [["1", "2", "3"], ["A", "C", "E"]],
        [["4", "5"], ["B", None]],
    ]
    gab = cq.extrair_gabarito_de_tabelas(tabelas)
    assert gab == {1: "A", 2: "C", 3: "E", 4: "B"}


def test_casar_gabarito():
    questoes = [{"numero": 1}, {"numero": 3}]
    cq.casar_gabarito(questoes, {1: "A", 2: "C"})
    assert questoes[0]["gabarito"] == "A"
    assert questoes[1]["gabarito"] is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_coletor_quadrix.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar `banco_questoes\coletor_quadrix.py` (parte 1: parsers)**

```python
"""Coletor de provas em PDF da Quadrix: baixa, extrai questões e casa gabaritos."""
import re

import edital

RE_QUESTAO = re.compile(r"QUEST[ÃA]O\s+(\d+)")
RE_ALTERNATIVA = re.compile(r"\(([A-E])\)")


def _mapear_secoes(texto):
    """Posições onde cada matéria começa no texto (pelos títulos de seção)."""
    maiusculo = texto.upper()
    marcas = []
    for nome, dados in edital.MATERIAS.items():
        for padrao in dados["titulos_pdf"]:
            for m in re.finditer(re.escape(padrao), maiusculo):
                marcas.append((m.start(), nome))
    return sorted(marcas)


def _materia_na_posicao(marcas, pos):
    atual = None
    for inicio, nome in marcas:
        if inicio <= pos:
            atual = nome
        else:
            break
    return atual


def _limpar(texto):
    return " ".join(texto.split()).strip()


def extrair_questoes_do_texto(texto):
    """Retorna (questoes, numeros_pulados). Questão sem 2+ alternativas é pulada."""
    marcas = _mapear_secoes(texto)
    achados = list(RE_QUESTAO.finditer(texto))
    questoes, puladas = [], []
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        corpo = texto[m.end():fim]
        numero = int(m.group(1))
        partes = RE_ALTERNATIVA.split(corpo)
        enunciado = _limpar(partes[0])
        alternativas = {}
        for letra, trecho in zip(partes[1::2], partes[2::2]):
            alternativas[letra] = _limpar(trecho)
        if not enunciado or len(alternativas) < 2:
            puladas.append(numero)
            continue
        questoes.append({
            "numero": numero,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "materia": _materia_na_posicao(marcas, m.start()),
        })
    return questoes, puladas


def extrair_gabarito_de_tabelas(tabelas):
    """Tabelas do PDF de gabarito: linha de números seguida de linha de letras."""
    gabarito = {}
    for tabela in tabelas:
        for linha_num, linha_resp in zip(tabela, tabela[1:]):
            for num, resp in zip(linha_num, linha_resp):
                num = str(num or "").strip()
                resp = str(resp or "").strip().upper()
                if num.isdigit() and resp in "ABCDE" and resp:
                    gabarito[int(num)] = resp
    return gabarito


def casar_gabarito(questoes, gabarito):
    for q in questoes:
        q["gabarito"] = gabarito.get(q["numero"])
```

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_coletor_quadrix.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```powershell
git add banco_questoes
git commit -m "feat: parser de provas e gabaritos da Quadrix"
```

---

### Task 6: `coletor_quadrix.py` — download, processamento completo e relatório

**Files:**
- Modify: `banco_questoes\coletor_quadrix.py` (acrescentar ao final + lista `PROVAS` no topo)
- Test: `banco_questoes\tests\test_coletor_quadrix.py` (acrescentar)

**Interfaces:**
- Consumes: parsers da Task 5; `db.conectar`, `db.salvar_questao` (Task 1).
- Produces: `processar_prova(caminho_prova, caminho_gabarito, con, metadados: dict) -> dict` com chaves `salvas, duplicadas, puladas, sem_materia`; `baixar(url, destino: Path) -> Path` (cache: não re-baixa); CLI `python coletor_quadrix.py` que percorre `PROVAS`, grava no banco e escreve `relatorio_extracao.txt`.

- [ ] **Step 1: Acrescentar testes**

```python
import db


def test_processar_prova_texto(tmp_path, monkeypatch):
    con = db.conectar(tmp_path / "t.db")
    monkeypatch.setattr(cq, "_texto_do_pdf", lambda caminho: cq_texto_fake(caminho))
    monkeypatch.setattr(cq, "_tabelas_do_pdf",
                        lambda caminho: [[["1", "3"], ["A", "B"]]])
    resultado = cq.processar_prova("prova.pdf", "gab.pdf", con,
                                   {"banca": "Instituto Quadrix", "orgao": "CRT-4",
                                    "ano": 2024, "prova": "Assistente Administrativo"})
    assert resultado["salvas"] == 2
    assert resultado["puladas"] == [2]
    linha = con.execute("SELECT * FROM questoes WHERE materia='Língua Portuguesa'").fetchone()
    assert linha["gabarito"] == "A"
    assert linha["fonte"] == "quadrix_pdf"
    assert linha["id_qc"] is None
    # rodar de novo: tudo duplicado
    resultado2 = cq.processar_prova("prova.pdf", "gab.pdf", con, {"ano": 2024})
    assert resultado2["salvas"] == 0
    assert resultado2["duplicadas"] == 2


def cq_texto_fake(caminho):
    return TEXTO_PROVA


def test_baixar_usa_cache(tmp_path, monkeypatch):
    destino = tmp_path / "prova.pdf"
    destino.write_bytes(b"%PDF-cache")

    def explode(*a, **kw):
        raise AssertionError("não deveria baixar de novo")

    monkeypatch.setattr(cq.requests, "get", explode)
    assert cq.baixar("http://exemplo/prova.pdf", destino) == destino
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_coletor_quadrix.py -v`
Expected: os 2 novos FAIL.

- [ ] **Step 3: Implementar (acrescentar em `coletor_quadrix.py`)**

No topo do arquivo, junto dos imports:

```python
import sys
from pathlib import Path

import pdfplumber
import requests

import db

PASTA_PDFS = Path(__file__).resolve().parent / "provas_pdf"
ARQUIVO_RELATORIO = Path(__file__).resolve().parent / "relatorio_extracao.txt"

# Provas encerradas da Quadrix com matérias em comum com o edital (nível médio).
# Preencher pesquisando em https://www.quadrix.org.br (concursos encerrados):
# cada item precisa da URL do caderno de prova e do gabarito definitivo.
PROVAS = [
    # {"nome": "crt4_2024_assistente", "orgao": "CRT-4", "ano": 2024,
    #  "prova": "Assistente Administrativo",
    #  "url_prova": "https://.../caderno.pdf", "url_gabarito": "https://.../gabarito.pdf"},
]
```

Ao final do arquivo:

```python
def _texto_do_pdf(caminho):
    with pdfplumber.open(caminho) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _tabelas_do_pdf(caminho):
    with pdfplumber.open(caminho) as pdf:
        tabelas = []
        for pagina in pdf.pages:
            tabelas.extend(pagina.extract_tables())
        return tabelas


def baixar(url, destino):
    """Baixa a URL para destino, usando cache local (não re-baixa)."""
    destino = Path(destino)
    if destino.exists():
        return destino
    resposta = requests.get(url, timeout=60)
    resposta.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resposta.content)
    return destino


def processar_prova(caminho_prova, caminho_gabarito, con, metadados):
    """Extrai as questões de uma prova, casa o gabarito e salva no banco."""
    questoes, puladas = extrair_questoes_do_texto(_texto_do_pdf(caminho_prova))
    casar_gabarito(questoes, extrair_gabarito_de_tabelas(_tabelas_do_pdf(caminho_gabarito)))
    resultado = {"salvas": 0, "duplicadas": 0, "puladas": puladas, "sem_materia": 0}
    for q in questoes:
        if q["materia"] is None:
            resultado["sem_materia"] += 1
            continue
        salvou = db.salvar_questao(con, {
            "id_qc": None,
            "enunciado": q["enunciado"],
            "alternativas": q["alternativas"],
            "gabarito": q["gabarito"],
            "materia": q["materia"],
            "banca": metadados.get("banca", "Instituto Quadrix"),
            "orgao": metadados.get("orgao"),
            "ano": metadados.get("ano"),
            "prova": metadados.get("prova"),
            "fonte": "quadrix_pdf",
        })
        resultado["salvas" if salvou else "duplicadas"] += 1
    return resultado


def main():
    if not PROVAS:
        print("A lista PROVAS está vazia. Abra coletor_quadrix.py e adicione as URLs"
              " das provas da Quadrix que você quer importar.")
        return
    con = db.conectar()
    linhas_relatorio = []
    for prova in PROVAS:
        print(f"— {prova['nome']} —")
        try:
            caminho_prova = baixar(prova["url_prova"], PASTA_PDFS / f"{prova['nome']}_prova.pdf")
            caminho_gab = baixar(prova["url_gabarito"], PASTA_PDFS / f"{prova['nome']}_gabarito.pdf")
        except requests.exceptions.RequestException as erro:
            print(f"  Não consegui baixar ({erro.__class__.__name__})."
                  " Confira sua internet ou a URL e tente de novo.")
            continue
        r = processar_prova(caminho_prova, caminho_gab, con, prova)
        print(f"  salvas={r['salvas']} duplicadas={r['duplicadas']}"
              f" puladas={len(r['puladas'])} sem_materia={r['sem_materia']}")
        if r["puladas"]:
            linhas_relatorio.append(f"{prova['nome']}: questões puladas {r['puladas']}")
        if r["sem_materia"]:
            linhas_relatorio.append(f"{prova['nome']}: {r['sem_materia']} questões sem matéria reconhecida")
    if linhas_relatorio:
        ARQUIVO_RELATORIO.write_text("\n".join(linhas_relatorio), encoding="utf-8")
        print(f"Relatório de problemas: {ARQUIVO_RELATORIO}")
    con.close()


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Sem internet ou site fora do ar. Tente de novo mais tarde.")
        sys.exit(1)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_coletor_quadrix.py -v`
Expected: 5 PASS

- [ ] **Step 5: Preencher `PROVAS` com provas reais e rodar de verdade**

Pesquisar no site da Quadrix (concursos encerrados) 2–4 provas de nível médio com matérias em comum (ex.: CRT, CRF, CFO — cargos de assistente/técnico administrativo; ideal: provas anteriores da própria SEDES ou de órgãos do GDF). Copiar URL do caderno + gabarito definitivo para a lista `PROVAS`. Depois:

```powershell
..\.venv\Scripts\python.exe coletor_quadrix.py
..\.venv\Scripts\python.exe -c "import db; con=db.conectar(); print(con.execute('SELECT materia, COUNT(*) FROM questoes GROUP BY materia').fetchall())"
```

Expected: contagem > 0 em pelo menos Língua Portuguesa e Direito Administrativo; questões ilegíveis listadas no relatório, sem aborto. Se o parser falhar num layout real, ajustar regex/títulos e **acrescentar o trecho problemático como caso de teste**.

- [ ] **Step 6: Commit**

```powershell
git add banco_questoes
git commit -m "feat: download com cache, processamento de provas e relatorio"
```

---

### Task 7: `scraper_qc.py` — fixture HTML + parser de blocos de questão

**Files:**
- Create: `banco_questoes\scraper_qc.py`
- Create: `banco_questoes\salvar_html_exemplo.py` (helper descartável)
- Create: `banco_questoes\tests\fixtures\pagina_qc.html` (gerada no Step 1)
- Test: `banco_questoes\tests\test_scraper_qc.py`

**Interfaces:**
- Consumes: nada novo.
- Produces: `SELETORES: dict[str, str]` (seletores CSS centralizados no topo); `extrair_blocos(html: str) -> list[dict]` — cada dict com `id_qc, enunciado, alternativas, materia_qc, assunto, ano, banca, orgao, prova` (strings cruas do site; `ano` int ou None); `abrir_chrome() -> webdriver.Chrome` (perfil logado do usuário).

- [ ] **Step 1: Capturar uma página real do QC como fixture**

Instalar Playwright: `..\.venv\Scripts\python.exe -m pip install playwright`
(com `channel="chrome"` ele usa o Chrome já instalado — não precisa de `playwright install`).

Criar `banco_questoes\salvar_html_exemplo.py`:

```python
"""Abre o Chrome (perfil dedicado do scraper), espera você logar no QC
e salva o HTML da lista de questões como fixture. Seu Chrome normal pode
ficar aberto — o scraper usa um perfil separado."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PERFIL = Path(__file__).resolve().parent / "perfil_chrome_scraper"
URL = "https://www.qconcursos.com/questoes-de-concursos/questoes"

with sync_playwright() as p:
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL), channel="chrome", headless=False)
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    pagina.goto(URL)
    print("Janela aberta. Faça login no QConcursos nela (se ainda não estiver).")
    print("O script salva sozinho quando as questões aparecerem (até 10 min).")
    html = ""
    for _ in range(120):
        html = pagina.content()
        if re.search(r"Q\d{5,}", html):
            break
        time.sleep(5)
    destino = Path(__file__).parent / "tests" / "fixtures" / "pagina_qc.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"Salvo: {destino} ({destino.stat().st_size} bytes)")
    contexto.close()
```

Adicionar `banco_questoes/perfil_chrome_scraper/` ao `.gitignore` da raiz.

Run: `..\.venv\Scripts\python.exe salvar_html_exemplo.py`
Expected: arquivo `tests\fixtures\pagina_qc.html` criado com centenas de KB. **Abrir o arquivo e anotar:** o seletor do bloco de cada questão, do código `Qxxxxx`, do enunciado, das alternativas e da linha de metadados (banca/órgão/ano). No QC atual os blocos costumam ser `div.q-question-item`, com id em `.q-id`, enunciado em `.q-question-enunciation`, alternativas em `.q-item-choice` e metadados em `.q-question-info` — **confirmar na fixture e corrigir no Step 3 se mudou**.

- [ ] **Step 2: Escrever teste contra a fixture** — `banco_questoes\tests\test_scraper_qc.py`:

```python
from pathlib import Path

import pytest

import scraper_qc

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_qc.html"


@pytest.fixture
def html():
    if not FIXTURE.exists():
        pytest.skip("fixture pagina_qc.html ainda não capturada")
    return FIXTURE.read_text(encoding="utf-8")


def test_extrai_blocos_da_pagina_real(html):
    blocos = scraper_qc.extrair_blocos(html)
    assert len(blocos) >= 5  # uma página de busca tem vários resultados
    primeiro = blocos[0]
    assert primeiro["id_qc"].startswith("Q")
    assert len(primeiro["enunciado"]) > 20
    assert len(primeiro["alternativas"]) >= 2
    letras = set(primeiro["alternativas"])
    assert letras <= set("ABCDE") or letras == {"C", "E"}
    assert primeiro["ano"] is None or isinstance(primeiro["ano"], int)
```

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_scraper_qc.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar `banco_questoes\scraper_qc.py` (parte 1: parser)**

```python
"""Scraper do QConcursos usando Playwright (Chrome, perfil dedicado) + BS4.

Se o site mudar de layout, ajuste apenas o dicionário SELETORES abaixo.
Primeira execução abre janela para login; depois roda invisível (headless).
"""
import re
from pathlib import Path

from bs4 import BeautifulSoup

# ── SELETORES CENTRALIZADOS (ajustar aqui se o QC mudar o layout) ──────────
SELETORES = {
    "bloco": "div.q-question-item",
    "id": ".q-id",
    "enunciado": ".q-question-enunciation",
    "alternativa": ".q-item-choice",
    "letra_alternativa": ".q-item-enum",
    "info": ".q-question-info",           # linha com Ano/Banca/Órgão/Prova
    "breadcrumb": ".q-question-breadcrumb",  # matéria e assunto
}

PERFIL_CHROME = Path(__file__).resolve().parent / "perfil_chrome_scraper"


def _texto(no):
    return " ".join(no.get_text(" ").split()) if no else ""


def extrair_blocos(html):
    """Extrai todas as questões de uma página de busca do QC."""
    sopa = BeautifulSoup(html, "html.parser")
    questoes = []
    for bloco in sopa.select(SELETORES["bloco"]):
        id_qc = _texto(bloco.select_one(SELETORES["id"]))
        id_match = re.search(r"Q\d+", id_qc)
        alternativas = {}
        for i, alt in enumerate(bloco.select(SELETORES["alternativa"])):
            letra_no = alt.select_one(SELETORES["letra_alternativa"])
            letra = _texto(letra_no)[:1].upper() if letra_no else "ABCDE"[i]
            texto_alt = _texto(alt)
            if letra_no:
                texto_alt = texto_alt.replace(_texto(letra_no), "", 1).strip()
            alternativas[letra] = texto_alt
        info = _texto(bloco.select_one(SELETORES["info"]))
        ano = re.search(r"Ano[:\s]+(\d{4})", info)
        banca = re.search(r"Banca[:\s]+([^|•]+)", info)
        orgao = re.search(r"[ÓO]rg[ãa]o[:\s]+([^|•]+)", info)
        prova = re.search(r"Prova[:\s]+([^|•]+)", info)
        trilha = _texto(bloco.select_one(SELETORES["breadcrumb"]))
        partes_trilha = [p.strip() for p in trilha.split(">") if p.strip()]
        questoes.append({
            "id_qc": id_match.group(0) if id_match else None,
            "enunciado": _texto(bloco.select_one(SELETORES["enunciado"])),
            "alternativas": alternativas,
            "materia_qc": partes_trilha[0] if partes_trilha else None,
            "assunto": partes_trilha[1] if len(partes_trilha) > 1 else None,
            "ano": int(ano.group(1)) if ano else None,
            "banca": banca.group(1).strip() if banca else None,
            "orgao": orgao.group(1).strip() if orgao else None,
            "prova": prova.group(1).strip() if prova else None,
        })
    return [q for q in questoes if q["id_qc"] and q["enunciado"] and q["alternativas"]]
```

**Importante:** ao rodar o teste, se vier lista vazia ou campo errado, abrir a fixture, corrigir `SELETORES` (só o dicionário) e rodar de novo até passar. Essa é a calibração prevista no design.

- [ ] **Step 4: Rodar e ver passar**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_scraper_qc.py -v`
Expected: 1 PASS (com a fixture real).

- [ ] **Step 5: Commit**

```powershell
git add banco_questoes
git commit -m "feat: parser de blocos de questao do QConcursos com fixture real"
```

---

### Task 8: `scraper_qc.py` — navegação, paginação e coleta incremental

**Files:**
- Modify: `banco_questoes\scraper_qc.py` (acrescentar)
- Modify: `banco_questoes\edital.py` (preencher `url_qc` de cada matéria — Step 1)
- Test: `banco_questoes\tests\test_scraper_qc.py` (acrescentar)

**Interfaces:**
- Consumes: `extrair_blocos` (Task 7); `db.salvar_questao`, `db.obter_progresso`, `db.salvar_progresso` (Tasks 1–2); `edital.MATERIAS["..."]["url_qc"]` (Task 3).
- Produces: `abrir_chrome() -> webdriver.Chrome`; `url_pagina(url_base: str, pagina: int) -> str`; `salvar_pagina(html, con, materia: str) -> int` (nº de questões novas salvas); CLI `python scraper_qc.py` (fase de enunciados, retomável).

- [ ] **Step 1: Preencher `url_qc` no `edital.py`**

Com o Chrome normal, logado no QC: para cada matéria, montar a busca em `https://www.qconcursos.com/questoes-de-concursos/questoes` com os filtros de disciplina/assunto do edital + marcar "excluir anuladas" e "excluir desatualizadas". **Não filtrar por banca** — o conteúdo do edital aparece em provas de várias bancas e todas interessam (a banca de cada questão fica registrada no campo `banca`). Copiar a URL do navegador e colar no campo `url_qc` da matéria em `edital.py`. (Os IDs de filtro do QC só aparecem na URL depois de aplicar os filtros no site — por isso esse passo é manual e feito uma única vez.)

- [ ] **Step 2: Acrescentar testes**

```python
def test_url_pagina():
    assert scraper_qc.url_pagina("https://x.com/q?a=1", 3) == "https://x.com/q?a=1&page=3"
    assert scraper_qc.url_pagina("https://x.com/q", 2) == "https://x.com/q?page=2"


def test_salvar_pagina_grava_no_banco(html, tmp_path):
    import db
    con = db.conectar(tmp_path / "t.db")
    novas = scraper_qc.salvar_pagina(html, con, "Língua Portuguesa")
    assert novas >= 5
    linha = con.execute("SELECT * FROM questoes LIMIT 1").fetchone()
    assert linha["fonte"] == "qconcursos"
    assert linha["materia"] == "Língua Portuguesa"
    # de novo: tudo duplicado
    assert scraper_qc.salvar_pagina(html, con, "Língua Portuguesa") == 0
```

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_scraper_qc.py -v`
Expected: os 2 novos FAIL.

- [ ] **Step 3: Implementar (acrescentar em `scraper_qc.py`)**

```python
import random
import sys
import time

from playwright.sync_api import sync_playwright

import db
import edital

PAUSA_MIN, PAUSA_MAX = 3, 6
MAX_PAGINAS_POR_MATERIA = 40  # limite por sessão diária, por educação
HEADLESS = False  # o Cloudflare do QC bloqueia navegador invisível ("Um momento…");
                  # a coleta roda com janela visível — pode minimizar que ela trabalha sozinha


def abrir_navegador(p, headless=HEADLESS):
    """Chrome com o perfil dedicado do scraper (login fica salvo nele)."""
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL_CHROME), channel="chrome", headless=headless)
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    return contexto, pagina


def url_pagina(url_base, pagina):
    separador = "&" if "?" in url_base else "?"
    return f"{url_base}{separador}page={pagina}"


def salvar_pagina(html, con, materia):
    """Salva as questões de uma página no banco; retorna quantas eram novas."""
    novas = 0
    for q in extrair_blocos(html):
        salvou = db.salvar_questao(con, {
            "id_qc": q["id_qc"],
            "enunciado": q["enunciado"],
            "alternativas": q["alternativas"],
            "gabarito": None,
            "materia": materia,
            "assunto": q["assunto"],
            "banca": q["banca"],
            "orgao": q["orgao"],
            "ano": q["ano"],
            "prova": q["prova"],
            "fonte": "qconcursos",
        })
        novas += 1 if salvou else 0
    return novas


def _pausa():
    time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))


def coletar_enunciados():
    con = db.conectar()
    with sync_playwright() as p:
        contexto, aba = abrir_navegador(p)
        try:
            for materia in edital.nomes_materias():
                url_base = edital.MATERIAS[materia]["url_qc"]
                if not url_base:
                    print(f"[{materia}] sem url_qc no edital.py — pulando.")
                    continue
                pagina = db.obter_progresso(con, materia) + 1
                fim = pagina + MAX_PAGINAS_POR_MATERIA
                while pagina < fim:
                    aba.goto(url_pagina(url_base, pagina))
                    _pausa()
                    html = aba.content()
                    novas = salvar_pagina(html, con, materia)
                    total_blocos = len(extrair_blocos(html))
                    print(f"[{materia}] página {pagina}: {novas} novas ({total_blocos} na página)")
                    db.salvar_progresso(con, materia, pagina)
                    if total_blocos == 0:  # acabaram as páginas (ou caiu o login)
                        break
                    pagina += 1
        finally:
            contexto.close()
            con.close()


if __name__ == "__main__":
    try:
        coletar_enunciados()
    except KeyboardInterrupt:
        print("\nInterrompido — o progresso por página já ficou salvo. Rode de novo para retomar.")
    except Exception as erro:  # rede, site fora etc.
        print(f"Erro inesperado ({erro.__class__.__name__}: {erro}).")
        print("Confira internet/login no QC e rode de novo — a coleta retoma de onde parou.")
        sys.exit(1)
```

- [ ] **Step 4: Rodar testes**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_scraper_qc.py -v`
Expected: 3 PASS

- [ ] **Step 5: Rodada real supervisionada**

Rodar `..\.venv\Scripts\python.exe scraper_qc.py` (não precisa fechar seu Chrome — o scraper usa perfil próprio) e observar 2–3 páginas da primeira matéria; conferir no banco:

```powershell
..\.venv\Scripts\python.exe -c "import db; con=db.conectar(); print(con.execute('SELECT materia, COUNT(*) FROM questoes GROUP BY materia').fetchall()); print(con.execute('SELECT * FROM progresso_scraper').fetchall())"
```

Expected: contagens subindo e progresso salvo. Pode interromper com Ctrl+C e rodar de novo — deve retomar da página seguinte.

- [ ] **Step 6: Commit**

```powershell
git add banco_questoes
git commit -m "feat: coleta paginada e retomavel de enunciados do QC"
```

---

### Task 9: `scraper_qc.py` — fase de gabaritos (cota diária da conta free)

**Files:**
- Modify: `banco_questoes\scraper_qc.py` (acrescentar `coletar_gabaritos` + seletores)
- Test: `banco_questoes\tests\test_scraper_qc.py` (acrescentar teste de detecção de limite)

**Interfaces:**
- Consumes: `db.sem_gabarito`, `db.atualizar_gabarito` (Task 2); `abrir_chrome` (Task 8).
- Produces: `atingiu_limite(html: str) -> bool`; `extrair_resposta(html: str) -> tuple[str|None, str|None]` (gabarito, comentário); CLI `python scraper_qc.py gabaritos`.

- [ ] **Step 1: Acrescentar seletores e testes**

Acrescentar ao dicionário `SELETORES` (confirmar numa página de questão real e ajustar):

```python
    "botao_responder": "a.js-question-answer, button.q-answer-button",
    "resposta_certa": ".q-question-feedback .q-answer, .js-question-right-answer",
    "comentario_prof": ".q-question-comments .q-item-comment",
    "aviso_limite": ".q-limit-modal, .js-premium-block",
```

Testes (HTML mínimo inline — não precisa de fixture nova):

```python
def test_atingiu_limite():
    assert scraper_qc.atingiu_limite('<div class="q-limit-modal">Você atingiu o limite diário</div>')
    assert not scraper_qc.atingiu_limite("<div>página normal</div>")


def test_extrair_resposta():
    html_resp = ('<div class="q-question-feedback"><span class="q-answer">B</span></div>'
                 '<div class="q-question-comments"><div class="q-item-comment">'
                 'Gabarito B porque sim.</div></div>')
    gabarito, comentario = scraper_qc.extrair_resposta(html_resp)
    assert gabarito == "B"
    assert "porque sim" in comentario


def test_extrair_resposta_sem_nada():
    assert scraper_qc.extrair_resposta("<div></div>") == (None, None)
```

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_scraper_qc.py -v`
Expected: os 3 novos FAIL.

- [ ] **Step 2: Implementar (acrescentar em `scraper_qc.py`)**

```python
def atingiu_limite(html):
    sopa = BeautifulSoup(html, "html.parser")
    if sopa.select_one(SELETORES["aviso_limite"]):
        return True
    return "limite diário" in sopa.get_text(" ").lower()


def extrair_resposta(html):
    """Depois de responder: retorna (letra_do_gabarito, comentario_ou_None)."""
    sopa = BeautifulSoup(html, "html.parser")
    resposta = sopa.select_one(SELETORES["resposta_certa"])
    letra = _texto(resposta)[:1].upper() if resposta else None
    if letra not in ("A", "B", "C", "D", "E"):
        letra = None
    comentario = _texto(sopa.select_one(SELETORES["comentario_prof"])) or None
    return letra, comentario


def coletar_gabaritos():
    con = db.conectar()
    pendentes = db.sem_gabarito(con)
    if not pendentes:
        print("Nenhuma questão pendente de gabarito. 🎉")
        con.close()
        return
    print(f"{len(pendentes)} questões sem gabarito; usando a cota diária…")
    coletadas = 0
    with sync_playwright() as p:
        contexto, aba = abrir_navegador(p)
        try:
            for q in pendentes:
                numero = q["id_qc"].lstrip("Q")
                aba.goto(f"https://www.qconcursos.com/questoes-de-concursos/questoes/{numero}")
                _pausa()
                if atingiu_limite(aba.content()):
                    print(f"Limite diário do QC atingido. Coletados {coletadas} gabaritos hoje;"
                          " rode de novo amanhã.")
                    break
                # marca a 1ª alternativa e clica em responder (só queremos o feedback)
                try:
                    aba.click(SELETORES["alternativa"], timeout=5000)
                    aba.click(SELETORES["botao_responder"], timeout=5000)
                except Exception:
                    print(f"  {q['id_qc']}: não achei o botão de responder — pulando.")
                    continue
                _pausa()
                gabarito, comentario = extrair_resposta(aba.content())
                if gabarito:
                    db.atualizar_gabarito(con, q["id_qc"], gabarito, comentario)
                    coletadas += 1
                    print(f"  {q['id_qc']}: {gabarito}" + (" (com comentário)" if comentario else ""))
                else:
                    print(f"  {q['id_qc']}: resposta não localizada — pulando.")
        finally:
            contexto.close()
            con.close()
    print(f"Fase de gabaritos encerrada: {coletadas} coletados.")
```

E trocar o bloco final do arquivo por:

```python
if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "enunciados"
    try:
        if fase == "gabaritos":
            coletar_gabaritos()
        else:
            coletar_enunciados()
    except KeyboardInterrupt:
        print("\nInterrompido — progresso salvo. Rode de novo para retomar.")
    except Exception as erro:
        print(f"Erro inesperado ({erro.__class__.__name__}: {erro}).")
        print("Confira internet/login no QC e rode de novo.")
        sys.exit(1)
```

- [ ] **Step 3: Rodar testes**

Run: `..\.venv\Scripts\python.exe -m pytest -v`
Expected: suíte inteira PASS.

- [ ] **Step 4: Rodada real supervisionada da fase de gabaritos**

`..\.venv\Scripts\python.exe scraper_qc.py gabaritos` com poucas pendências; confirmar que gabaritos entram no banco e que o aviso de limite encerra sem traceback. Ajustar os 4 seletores novos se o site diferir (só o dicionário `SELETORES`).

- [ ] **Step 5: Commit final**

```powershell
git add banco_questoes
git commit -m "feat: coleta de gabaritos e comentarios com respeito a cota diaria"
```

---

## Rotina de uso diário (depois de pronto)

1. `..\.venv\Scripts\python.exe scraper_qc.py` — coleta enunciados (retomável).
2. `..\.venv\Scripts\python.exe scraper_qc.py gabaritos` — gasta a cota do dia.
3. `..\.venv\Scripts\python.exe coletor_quadrix.py` — só quando adicionar provas novas.
4. `..\.venv\Scripts\python.exe -m simulados.questoes_portugues` (ou outra matéria) — gera o PDF do dia.
5. `..\.venv\Scripts\python.exe -m simulados.zerar_usadas` — quando quiser reciclar questões.
