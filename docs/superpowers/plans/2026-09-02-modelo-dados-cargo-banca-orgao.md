# Modelo de Dados: Cargo/Banca/Órgão Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o banco gravar de verdade `banca`/`orgao`/`cargo` por questão (hoje descartados silenciosamente no INSERT) e extrair `cargo`/`categoria`/`tema` direto do HTML do QConcursos no momento da coleta, sem depender de contexto externo.

**Architecture:** Correção cirúrgica em dois arquivos existentes (`banco_questoes/db.py`, `banco_questoes/scraper_qc.py`), sem mudança de schema (as colunas já existem via `migrations/migration_001.py` e `migration_002.py`) e sem reestruturação de pastas (isso é a Fase 4 do roadmap maior — ver "Fases futuras" no fim deste documento).

**Tech Stack:** Python 3.14, psycopg2, BeautifulSoup4, pytest, PostgreSQL 18 (local, nativo — sem Docker).

**Spec:** `banco_questoes/CLAUDE.md` (regras de arquitetura/código do projeto) + decisões da sessão de brainstorming de 2026-09-02 (registradas abaixo, já que não existe um spec formal separado para esta mudança pontual).

## Global Constraints

- Tipagem estrita em toda assinatura de função nova ou modificada (`CLAUDE.md` §3).
- Proibido `# TODO`/reticências em código crítico de scraping e persistência (`CLAUDE.md` §3).
- Erro de layout/seletor quebrado é tratado localmente, retornando campo nulo — nunca derruba a extração inteira da página (`CLAUDE.md` §3).
- Conexão de banco é injetada (recebida como parâmetro já aberta); proibido abrir conexão nova dentro de loop ou função auxiliar (`CLAUDE.md` §2).
- Limite de 150 linhas por arquivo (`CLAUDE.md` §1) **não** se aplica ainda a `scraper_qc.py` (438 linhas) nem `db.py` (304 linhas) — são arquivos existentes que já excedem o limite; dividi-los em camadas (`core/scraper.py`, `core/parser.py`, `storage/database.py`) é trabalho da Fase 4 (unificação + regras), feito só depois que a Fase 3 (organização de pastas) definir o que sobrevive. Nesta fase, só adicionamos/editamos funções pontuais nos arquivos como estão.
- Cargo só é gravado quando extraído da 1ª "Prova" listada no campo de metadados da questão do QConcursos — nunca inventado ou adivinhado (decisão do usuário, brainstorming 2026-09-02).
- PCI não grava `cargo` — a fonte não expõe esse dado por questão (confirmado: nenhum HTML/seletor de PCI referencia cargo). Fica `NULL`; o cruzamento com cargo acontece só na geração do PDF, casando por matéria/conteúdo com o YAML do edital.
- Quando o breadcrumb do QConcursos tiver mais de 3 níveis (matéria + 2), o nível mais granular (4º+) é descartado — o schema atual só tem colunas para `categoria` e `tema` (um nível cada). Registrado aqui para não ser um placeholder disfarçado: é uma simplificação deliberada, não uma lacuna esquecida.

---

## Contexto da bug encontrada (Task 0)

Durante a checagem inicial (RED da Task 1), a suíte inteira travava indefinidamente rodando contra o Postgres local. Investigação (`pg_stat_activity`) mostrou a causa raiz, **não relacionada** ao bug de cargo/banca/orgao:

1. `db.conectar()` reaplica `SQL_CRIAR` **e** as duas migrations (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) em **toda chamada** — e `ALTER TABLE` sempre pede `AccessExclusiveLock` na tabela inteira, mesmo quando a coluna já existe.
2. Nenhum teste em `tests/test_db.py` fecha a conexão (`con.close()`) no final. A conexão psycopg2 por padrão não está em `autocommit`, então um `SELECT` sozinho (ex.: dentro de `sortear_questoes`) deixa a transação aberta ("idle in transaction") até alguém chamar `commit()`/`close()` — o que nunca acontece.
3. Resultado: depois de 2-3 testes, sobra uma conexão "idle in transaction" seguindo um `AccessShareLock` pendurado; a próxima `db.conectar()` (chamada pelo fixture autouse `banco_de_teste_skip_multibanca` antes de CADA teste) trava esperando `AccessExclusiveLock` pra rodar a migration — que nunca é liberado. A suíte inteira empaca.

Isso bloqueia qualquer verificação automatizada das Tasks 1-4, então vira **Task 0**, resolvida primeiro.

---

### Task 0: Corrigir trava de conexão/migration em `db.conectar()`

**Files:**
- Modify: `banco_questoes/db.py:88-107` (função `conectar`)
- Test: `banco_questoes/tests/test_db.py` (adicionar ao final do arquivo)

**Interfaces:**
- Consumes: `psycopg2.connect`, `_Conexao` (já existe, sem mudança de assinatura)
- Produces: `db.conectar() -> _Conexao` (mesma assinatura pública; internamente liga `autocommit=True` na conexão psycopg2 subjacente e só roda as migrations uma vez por processo, via a flag de módulo `db._MIGRACOES_APLICADAS`)

- [x] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_db.py`:

```python
def test_conectar_liga_autocommit_para_nao_prender_transacao_aberta():
    """Sem autocommit, um SELECT sozinho deixa a conexão 'idle in transaction'
    até alguém commitar/fechar — isso é o que trava a suíte inteira quando
    vários testes abrem conexão e não fecham (ver Task 0 do plano)."""
    import psycopg2.extensions as ext
    con = db.conectar()
    con.execute("SELECT 1")
    assert con._con.get_transaction_status() == ext.TRANSACTION_STATUS_IDLE
    con.close()


def test_migracoes_rodam_uma_unica_vez_por_processo(monkeypatch):
    """ALTER TABLE (dentro das migrations) pede AccessExclusiveLock mesmo com
    IF NOT EXISTS. Rodar isso em toda chamada de conectar() é o que causa a
    fila de locks quando o processo tem várias conexões vivas ao mesmo tempo."""
    import migrations.migration_002 as m2
    chamadas = []
    monkeypatch.setattr(m2, "aplicar", lambda con: chamadas.append(1))
    monkeypatch.setattr(db, "_MIGRACOES_APLICADAS", False)

    con1 = db.conectar()
    con2 = db.conectar()

    assert len(chamadas) == 1
    con1.close()
    con2.close()
```

- [x] **Step 2: Rodar e confirmar que falham**

Run: `cd banco_questoes && source .venv/bin/activate && python3 -m pytest tests/test_db.py -q -k "autocommit or migracoes_rodam"`
Expected: **FAIL** — `test_conectar_liga_autocommit...` falha porque `get_transaction_status()` retorna `TRANSACTION_STATUS_INTRANS` (não `IDLE`); `test_migracoes_rodam_uma_unica_vez...` falha porque `len(chamadas) == 2`, não `1`.

Se o comando travar (não retornar em ~10s): há uma conexão zumbi de uma rodada anterior. Rode antes:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('banco_questoes_test','banco_questoes') AND pid <> pg_backend_pid();"
```

- [x] **Step 3: Implementar o mínimo pra passar**

Em `banco_questoes/db.py`, adicionar logo abaixo de `FONTES_VALIDAS` (perto do topo do arquivo):

```python
_MIGRACOES_APLICADAS = False
```

Substituir a função `conectar` (linhas 88-107) por:

```python
def conectar(caminho=None):
    """Abre conexão com o PostgreSQL e garante que as tabelas existam.

    `caminho` é um parâmetro legado (do tempo do SQLite) mantido só por
    compatibilidade retroativa com chamadas existentes; é ignorado — a
    conexão sempre usa `DATABASE_URL` (de config.py).
    """
    global _MIGRACOES_APLICADAS

    con = _Conexao(psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor))
    con._con.autocommit = True
    con.execute(SQL_CRIAR)

    if not _MIGRACOES_APLICADAS:
        try:
            from migrations import migration_001, migration_002
            migration_001.aplicar(con)
            migration_002.aplicar(con)
            _MIGRACOES_APLICADAS = True
        except ImportError:
            pass  # Migrations not available (should not happen in normal use)

    return con
```

(`con.commit()` depois de `SQL_CRIAR` foi removido — é no-op com `autocommit=True` e o statement já se auto-commitou.)

- [x] **Step 4: Rodar e confirmar que passam**

Run: `python3 -m pytest tests/test_db.py -q -k "autocommit or migracoes_rodam"`
Expected: **PASS**, 2 testes.

- [x] **Step 5: Rodar a suíte de `test_db.py` inteira pra checar que nada quebrou**

Run: `python3 -m pytest tests/test_db.py -q`
Expected: PASS em todos os testes existentes, sem travar. Preste atenção especial em `test_fonte_invalida_raises_error` e `test_dedupe_por_id_qc`/`test_dedupe_por_hash_enunciado` — são os que exercitam o `except psycopg2.errors.UniqueViolation: con.rollback()` em `salvar_questao`. Isso já foi verificado manualmente como seguro sob `autocommit=True` (não lança erro, conexão continua usável), mas confirme aqui.

- [x] **Step 6: Commit**

```bash
cd /home/salati/Documentos/projetos
git add banco_questoes/db.py banco_questoes/tests/test_db.py
git commit -m "fix: evita trava de conexao/migration em db.conectar()

autocommit=True impede SELECT solto de prender transacao aberta; guarda
de modulo evita reaplicar ALTER TABLE (AccessExclusiveLock) em toda
chamada. Sem isso a suite inteira empacava depois de poucos testes."
```

---

### Task 1: `salvar_questao` grava `banca`/`orgao`/`cargo`

**Files:**
- Modify: `banco_questoes/db.py:124-171` (função `salvar_questao`)
- Test: `banco_questoes/tests/test_db.py`

**Interfaces:**
- Consumes: dict `q` com chaves opcionais `banca`, `orgao`, `cargo` (já aceitas por `questao_exemplo()` no teste, e já testadas indiretamente em `test_salvar_questao_com_cargo`/`test_sortear_questoes_com_cargo`, que hoje falham)
- Produces: nenhuma mudança de assinatura — `salvar_questao(con, q) -> bool`, igual hoje

- [x] **Step 1: Confirmar que os testes já existentes falham (RED)**

Esses testes já existem em `tests/test_db.py` (linhas 148-257) mas nunca passaram porque o INSERT não grava as colunas:

Run: `python3 -m pytest tests/test_db.py -q -k "cargo"`
Expected: **FAIL** em `test_salvar_questao_com_cargo` (assert `linhas[0]["cargo"] == "Policial Rodoviário Federal"` falha porque a coluna fica `NULL`) e nos testes de filtro (`test_sortear_questoes_com_cargo`, etc. — resultado vazio porque o filtro `cargo=%s` nunca casa com nada).

- [x] **Step 2: Escrever o teste que falta (banca/orgao não têm assert direto ainda)**

Adicionar em `tests/test_db.py`:

```python
def test_salvar_questao_persiste_banca_e_orgao():
    """banca/orgao são usados como filtro em sortear_questoes mas nenhum
    teste checava a coluna direto — cobrindo o mesmo bug do cargo."""
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(
        id_qc="QBANCAORGAO1",
        enunciado="Teste banca e orgao",
        banca="Cebraspe",
        orgao="PRF",
    ))
    linha = con.execute(
        "SELECT banca, orgao FROM questoes WHERE enunciado=%s",
        ("Teste banca e orgao",),
    ).fetchone()
    assert linha["banca"] == "Cebraspe"
    assert linha["orgao"] == "PRF"
    con.close()
```

- [x] **Step 3: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_db.py -q -k "persiste_banca_e_orgao"`
Expected: **FAIL** — `linha["banca"]` é `None`, não `"Cebraspe"`.

- [x] **Step 4: Implementar — incluir as 3 colunas no INSERT**

Em `banco_questoes/db.py`, substituir o bloco do `INSERT` dentro de `salvar_questao` (linhas 142-166) por:

```python
        con.execute(
            "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, content_hash, alternativas,"
            " gabarito, comentario, materia, assunto, ano, prova, fonte,"
            " texto_associado, imagens, categoria, tema, imagens_urls,"
            " banca, orgao, cargo)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                q.get("id_qc"),
                q["enunciado"],
                hash_enunciado(q["enunciado"]),
                c_hash,
                json.dumps(q["alternativas"], ensure_ascii=False),
                q.get("gabarito"),
                q.get("comentario"),
                q["materia"],
                q.get("assunto"),
                q.get("ano"),
                q.get("prova"),
                fonte,
                q.get("texto_associado"),
                json.dumps(q["imagens"], ensure_ascii=False) if q.get("imagens") else None,
                q.get("categoria"),
                q.get("tema"),
                json.dumps(q.get("imagens_urls", []), ensure_ascii=False),
                q.get("banca"),
                q.get("orgao"),
                q.get("cargo"),
            ),
        )
```

- [x] **Step 5: Rodar e confirmar que passam**

Run: `python3 -m pytest tests/test_db.py -q -k "cargo or persiste_banca_e_orgao"`
Expected: **PASS** em todos (6 testes: os 5 de cargo já existentes + o novo de banca/orgao).

- [x] **Step 6: Rodar `test_db.py` inteiro**

Run: `python3 -m pytest tests/test_db.py -q`
Expected: PASS em todos, sem regressão.

- [x] **Step 7: Commit**

```bash
cd /home/salati/Documentos/projetos
git add banco_questoes/db.py banco_questoes/tests/test_db.py
git commit -m "fix: salvar_questao grava banca/orgao/cargo (antes descartados)

As colunas existiam desde migration_001/002 mas o INSERT nunca as
incluia, entao ficavam sempre NULL e o filtro de sortear_questoes por
banca/orgao/cargo nunca funcionava de verdade."
```

---

### Task 2: `scraper_qc.py` extrai `cargo` do campo "Prova"

**Files:**
- Modify: `banco_questoes/scraper_qc.py:79-96` (constantes/helpers de metadados)
- Test: `banco_questoes/tests/test_scraper_qc.py`

**Interfaces:**
- Consumes: `campos: dict` retornado por `_campos_info()` (chaves `"Ano"`, `"Banca"`, `"Órgão"`, `"Prova"`, já existente)
- Produces: `_extrair_cargo_da_prova(prova: str | None, banca: str | None, ano: str | None, orgao: str | None) -> str | None`, usada pela Task 3 dentro de `extrair_blocos`

Confirmado contra a fixture real (`tests/fixtures/pagina_qc.html`, bloco 0): campo `Prova` = `"IAN - 2026 - Câmara de Jardim - MS - Contador"`, onde banca="IAN", ano="2026", órgão="Câmara de Jardim - MS" (o órgão em si já tem hífen no nome — por isso a extração usa prefixo, não split por " - ").

- [x] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_scraper_qc.py`:

```python
def test_extrai_cargo_da_prova(html):
    blocos = scraper_qc.extrair_blocos(html)
    assert blocos[0]["cargo"] == "Contador"


def test_extrair_cargo_da_prova_isolada():
    # Órgão com hífen no nome — a extração não pode confundir com o
    # separador entre banca/ano/orgao/cargo.
    cargo = scraper_qc._extrair_cargo_da_prova(
        prova="IAN - 2026 - Câmara de Jardim - MS - Contador",
        banca="IAN", ano="2026", orgao="Câmara de Jardim - MS",
    )
    assert cargo == "Contador"


def test_extrair_cargo_da_prova_sem_dados_retorna_none():
    assert scraper_qc._extrair_cargo_da_prova(None, "IAN", "2026", "X") is None
    assert scraper_qc._extrair_cargo_da_prova("qualquer coisa", None, "2026", "X") is None
```

- [x] **Step 2: Rodar e confirmar que falham**

Run: `cd banco_questoes && source .venv/bin/activate && python3 -m pytest tests/test_scraper_qc.py -q -k "cargo_da_prova"`
Expected: **FAIL** com `AttributeError: module 'scraper_qc' has no attribute '_extrair_cargo_da_prova'` (ou `KeyError: 'cargo'` no primeiro teste).

- [x] **Step 3: Implementar o mínimo pra passar**

Em `banco_questoes/scraper_qc.py`, adicionar logo depois de `_campos_info` (depois da linha 96):

```python
def _extrair_cargo_da_prova(prova: str | None, banca: str | None,
                             ano: str | None, orgao: str | None) -> str | None:
    """Isola o cargo do texto de uma prova ("Banca - Ano - Órgão - Cargo").

    Usa banca/ano/órgão já extraídos como prefixo em vez de fazer split por
    " - ", porque o nome do órgão pode ter hífen (ex.: "Câmara de Jardim - MS").
    Só considera a 1ª prova quando há mais de uma (campo "Provas:" com "|").
    """
    if not prova or not banca or not ano or not orgao:
        return None
    primeira_prova = prova.split("|")[0].strip()
    prefixo = f"{banca} - {ano} - {orgao}"
    if not primeira_prova.startswith(prefixo):
        return None
    resto = primeira_prova[len(prefixo):].strip(" -")
    return resto or None
```

Depois, dentro de `extrair_blocos` (por volta da linha 114, logo após `campos = _campos_info(...)`), adicionar:

```python
        cargo = _extrair_cargo_da_prova(
            campos.get("Prova"), campos.get("Banca"),
            campos.get("Ano"), campos.get("Órgão"),
        )
```

E incluir `"cargo": cargo,` no dict retornado em `questoes.append({...})` (por volta da linha 122-134).

- [x] **Step 4: Rodar e confirmar que passam**

Run: `python3 -m pytest tests/test_scraper_qc.py -q -k "cargo_da_prova"`
Expected: **PASS**, 3 testes.

- [x] **Step 5: Commit**

```bash
cd /home/salati/Documentos/projetos
git add banco_questoes/scraper_qc.py banco_questoes/tests/test_scraper_qc.py
git commit -m "feat: extrai cargo do campo Prova no scraper do QConcursos

O texto de 'Prova' e Banca-Ano-Orgao-Cargo concatenados; usa os 3
primeiros ja extraidos como prefixo pra isolar o cargo, ja que o nome
do orgao pode ter hifen. So considera a 1a prova quando ha varias."
```

---

### Task 3: `scraper_qc.py` captura breadcrumb completo (`categoria`/`tema`)

**Files:**
- Modify: `banco_questoes/scraper_qc.py:99-135` (função `extrair_blocos`)
- Test: `banco_questoes/tests/test_scraper_qc.py`

**Interfaces:**
- Consumes: `SELETORES["breadcrumb"]` (já existe, `.q-question-breadcrumb`)
- Produces: chaves `"categoria"` e `"tema"` a mais no dict de cada questão retornado por `extrair_blocos` (além de `"assunto"`, que continua igual — não remover, outro código pode depender dela)

Confirmado contra a fixture (bloco 0): breadcrumb = `["Contabilidade Geral", "Legislação de Contabilidade", "Normas Brasileiras de Contabilidade - NBC"]` → matéria=1º link, categoria=2º link, tema=3º link. Quando existir um 4º nível, ele é descartado (ver Global Constraints).

- [x] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_scraper_qc.py`:

```python
def test_extrai_categoria_e_tema_do_breadcrumb(html):
    blocos = scraper_qc.extrair_blocos(html)
    assert blocos[0]["categoria"] == "Legislação de Contabilidade"
    assert blocos[0]["tema"] == "Normas Brasileiras de Contabilidade - NBC"
```

- [x] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_scraper_qc.py -q -k "categoria_e_tema"`
Expected: **FAIL** com `KeyError: 'categoria'`.

- [x] **Step 3: Implementar o mínimo pra passar**

Em `banco_questoes/scraper_qc.py`, dentro de `extrair_blocos`, substituir:

```python
        links_trilha = bloco.select(f"{SELETORES['breadcrumb']} a")
        materia_qc = _texto(links_trilha[0]) if links_trilha else None
        assunto = _texto(links_trilha[1]).rstrip(" ,") if len(links_trilha) > 1 else None
```

por:

```python
        links_trilha = bloco.select(f"{SELETORES['breadcrumb']} a")
        textos_trilha = [_texto(l).rstrip(" ,") for l in links_trilha]
        materia_qc = textos_trilha[0] if textos_trilha else None
        assunto = textos_trilha[1] if len(textos_trilha) > 1 else None
        categoria = textos_trilha[1] if len(textos_trilha) > 1 else None
        tema = textos_trilha[2] if len(textos_trilha) > 2 else None
```

E incluir `"categoria": categoria,` e `"tema": tema,` no dict retornado (junto de `"cargo": cargo,` da Task 2).

- [x] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_scraper_qc.py -q -k "categoria_e_tema"`
Expected: **PASS**.

- [x] **Step 5: Rodar `test_scraper_qc.py` inteiro**

Run: `python3 -m pytest tests/test_scraper_qc.py -q`
Expected: PASS em todos (inclui `test_extrai_blocos_da_pagina_real`, que não checa `categoria`/`tema`/`cargo` mas precisa continuar passando).

- [x] **Step 6: Commit**

```bash
cd /home/salati/Documentos/projetos
git add banco_questoes/scraper_qc.py banco_questoes/tests/test_scraper_qc.py
git commit -m "feat: captura categoria/tema do breadcrumb completo no QConcursos

Antes so pegava os 2 primeiros links do breadcrumb (materia+assunto).
Agora tambem preenche categoria/tema, alinhando com o schema que ja
o PCI usa. Quando o breadcrumb tem 4+ niveis, o mais granular e
descartado (schema so tem 1 coluna pra cada)."
```

---

### Task 4: `salvar_pagina` grava `cargo`/`categoria`/`tema` no banco

**Files:**
- Modify: `banco_questoes/scraper_qc.py:160-183` (função `salvar_pagina`)
- Test: `banco_questoes/tests/test_scraper_qc.py`

**Interfaces:**
- Consumes: dict retornado por `extrair_blocos` (agora com `cargo`/`categoria`/`tema`, Tasks 2-3), `db.salvar_questao` (assinatura inalterada, já aceita essas chaves desde a Task 1)
- Produces: nenhuma mudança de assinatura pública — `salvar_pagina(html, con, materia) -> int`, igual hoje

- [x] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_scraper_qc.py`:

```python
def test_salvar_pagina_grava_cargo_categoria_tema(html):
    import db
    con = db.conectar()
    scraper_qc.salvar_pagina(html, con, "Contabilidade Geral")
    linha = con.execute(
        "SELECT cargo, categoria, tema FROM questoes LIMIT 1"
    ).fetchone()
    assert linha["cargo"] == "Contador"
    assert linha["categoria"] == "Legislação de Contabilidade"
    assert linha["tema"] == "Normas Brasileiras de Contabilidade - NBC"
    con.close()
```

- [x] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_scraper_qc.py -q -k "salvar_pagina_grava_cargo"`
Expected: **FAIL** — as 3 colunas voltam `None` (o dict extraído já tem os campos desde a Task 2/3, mas `salvar_pagina` ainda não os repassa pro dict que vai pro banco).

- [x] **Step 3: Implementar o mínimo pra passar**

Em `banco_questoes/scraper_qc.py`, dentro de `salvar_pagina`, no dict passado pra `db.salvar_questao`, adicionar as 3 chaves:

```python
        salvou = db.salvar_questao(con, {
            "id_qc": q["id_qc"],
            "enunciado": q["enunciado"],
            "alternativas": q["alternativas"],
            "gabarito": None,
            "materia": materia,
            "assunto": q["assunto"],
            "categoria": q["categoria"],
            "tema": q["tema"],
            "cargo": q["cargo"],
            "banca": q["banca"],
            "orgao": "SEDES/DF",  # Força orgao SEDES/DF para matérias do edital
            "ano": q["ano"],
            "prova": q["prova"],
            "fonte": "qconcursos",
            "texto_associado": q["texto_associado"],
            "imagens": q["imagens"],
        })
```

- [x] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_scraper_qc.py -q -k "salvar_pagina_grava_cargo"`
Expected: **PASS**.

- [x] **Step 5: Commit**

```bash
cd /home/salati/Documentos/projetos
git add banco_questoes/scraper_qc.py banco_questoes/tests/test_scraper_qc.py
git commit -m "feat: salvar_pagina repassa cargo/categoria/tema pro banco

Fecha o fluxo: extrair_blocos ja extraia esses campos (Tasks 2-3), mas
salvar_pagina nao os incluia no dict passado pra db.salvar_questao."
```

---

### Task 5: Regressão completa

**Files:** nenhum (só verificação)

- [x] **Step 1: Rodar a suíte inteira (exceto os 4 arquivos com erro de import pré-existente, não relacionados a este plano — ver nota abaixo)**

```bash
cd banco_questoes && source .venv/bin/activate
python3 -m pytest tests/ -q \
  --ignore=tests/test_edital_loader.py \
  --ignore=tests/test_gerador_multibanca.py \
  --ignore=tests/test_gerar_simulado.py
```

Expected: PASS em tudo, sem travar (a trava da Task 0 não deve mais acontecer).

> Nota: `test_edital_loader.py`, `test_gerador_multibanca.py` e `test_gerar_simulado.py` falham na coleta por um bug de import pré-existente e não relacionado (`from banco_questoes import db` — módulo não encontrado quando rodado de dentro de `banco_questoes/`). Fora de escopo aqui; é candidato natural pra Fase 4 (unificação de imports).

- [x] **Step 2: Reportar ao usuário**

Resumo do que mudou, com os números de teste antes/depois, pronto pra decidir se seguimos pra Fase 2 (fluxo de PDF com foco PCDF/PMDF).

---

## Fases futuras (fora do escopo deste plano)

Ordem acordada com o usuário (brainstorming 2026-09-02), cada uma vira seu próprio plano quando chegar a vez:

- **Fase 2 — Fluxo de PDF com foco:** selecionar órgão/matéria/conteúdo → gerar PDF sorteado na pastinha do concurso (`estudo_autonomo/{orgao}/{cargo}/...`), com foco em PCDF/PMDF. Depende deste plano (o filtro por `cargo` só funciona depois da Task 1).
- **Fase 3 — Organização de pastas:** decidir o que fica/sai. Candidatos já identificados: `scrapers/qconcursos_materia.py` (redundante, não seta banca/orgao/cargo — comentário explícito "não preencher"), `scrapers/pci/coletor.py` v1 (substituído por `coletor_v2.py`), `scripts/migrate_pci_schema.py` (migration solta fora do sistema `migrations/`, referencia coluna `subcategoria` inexistente no schema atual), `banco_de_questoes.db`/`questoes.db` (resíduo SQLite pré-Postgres, já no `.gitignore`).
- **Fase 4 — Unificar + aplicar `CLAUDE.md` de verdade:** só depois que Fase 3 definir o que sobrevive, dividir os arquivos que hoje passam de 150 linhas (`scraper_qc.py`, `db.py`, `web_api.py`) na camada `core/scraper.py` (Playwright puro) / `core/parser.py` (BeautifulSoup puro, funções 100% puras) / `core/models.py` / `storage/database.py` / `main.py`, como o `CLAUDE.md` já define. Também é onde o bug de import inconsistente (`from banco_questoes import db` vs `import db`) se resolve de vez.
- **Fase 5 — Sincronização com tablet:** decisão de infra (cabo vs. WSL/Linux) + pastas de PDF sincronizadas (`PCDF/PDF...`, `PMDF/PDF...`).
