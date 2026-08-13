# Fase 2 — Simulado Geral, Dashboard Web e Docker · Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao banco de questões: estatísticas por matéria, Simulado Geral Completo proporcional ao edital, dashboard web (FastAPI) e empacotamento Docker (sem a coleta, que roda no host).

**Architecture:** Tudo dentro de `banco_questoes/` existente. `db.py` e `edital.py` ganham funções novas; `simulados/gerar_simulado.py` ganha `gerar_completo`; `web_api.py` (FastAPI) serve a API REST e a página estática `web/index.html`; `Dockerfile` + `docker-compose.yml` na raiz `training/` montam `banco_questoes/` como volume.

**Tech Stack:** Python 3.14 local (`training/.venv`), FastAPI + uvicorn + httpx (testes), ReportLab, SQLite. Docker com `python:3.12-slim` (a imagem instala as libs; o código vem por bind mount).

## Global Constraints

- Depende da Fase 1 completa (Tasks 1–6 do plano `2026-08-11-banco-questoes-sedes.md`; scraper das Tasks 7–9 pode estar em andamento — nada aqui importa `scraper_qc`, só dispara `scraper_qc.py` por subprocess).
- Comandos rodam de `c:\Users\Felps\Documents\training\banco_questoes` com `..\.venv\Scripts\python.exe`.
- PT-BR em código, mensagens e UI; código simples para iniciante.
- Quantidade do Simulado Geral é **sempre escolhida na hora** (formulário/parâmetro); a distribuição usa `edital.PESOS` (editável).
- A coleta nunca roda dentro do Docker: `COLETA_DISPONIVEL=0` no contêiner; a API responde 503 com mensagem clara e o botão da UI fica desabilitado.
- Nunca versionar: `.db`, PDFs, `perfil_chrome_scraper/` (já no `.gitignore`).
- Nomes canônicos de matéria idênticos aos de `edital.MATERIAS`.

---

### Task 1: `edital.PESOS` + distribuição proporcional + `db.estatisticas`

**Files:**
- Modify: `banco_questoes\edital.py` (acrescentar ao final)
- Modify: `banco_questoes\db.py` (acrescentar ao final)
- Test: `banco_questoes\tests\test_edital.py`, `banco_questoes\tests\test_db.py` (acrescentar)

**Interfaces:**
- Produces: `edital.PESOS: dict[str, int]` (mesmas 8 chaves de `MATERIAS`); `edital.distribuir_por_peso(quantidade: int) -> dict[str, int]` (soma == quantidade; maior-resto); `db.estatisticas(con) -> dict[str, dict]` com chaves `total, ineditas, usadas, sem_gabarito` por matéria (só matérias presentes no banco).

- [ ] **Step 1: Testes** — acrescentar em `tests\test_edital.py`:

```python
def test_pesos_cobrem_todas_as_materias():
    assert set(edital.PESOS) == set(edital.MATERIAS)
    assert all(p > 0 for p in edital.PESOS.values())


def test_distribuir_por_peso_soma_exata():
    for quantidade in (8, 20, 33, 60, 70):
        dist = edital.distribuir_por_peso(quantidade)
        assert sum(dist.values()) == quantidade
        assert set(dist) == set(edital.MATERIAS)


def test_distribuir_proporcional():
    dist = edital.distribuir_por_peso(60)
    # matéria de peso maior nunca recebe menos que uma de peso menor
    assert dist["Língua Portuguesa"] >= dist["Programas e Benefícios do DF"]
```

E em `tests\test_db.py`:

```python
def test_estatisticas(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_questao(con, questao_exemplo(id_qc="QA", enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="QB", enunciado="Dois?", gabarito=None))
    db.salvar_questao(con, questao_exemplo(id_qc="QC1", enunciado="Três?",
                                           materia="SUAS"))
    usada = db.sortear_questoes(con, "SUAS", 1)
    db.marcar_usadas(con, [usada[0]["id"]])
    est = db.estatisticas(con)
    assert est["Língua Portuguesa"] == {"total": 2, "ineditas": 2, "usadas": 0,
                                        "sem_gabarito": 1}
    assert est["SUAS"] == {"total": 1, "ineditas": 0, "usadas": 1, "sem_gabarito": 0}
```

- [ ] **Step 2: Rodar e ver falhar** — `..\.venv\Scripts\python.exe -m pytest tests\test_edital.py tests\test_db.py -v` → novos FAIL.

- [ ] **Step 3: Implementar** — ao final de `edital.py`:

```python
# Pesos para o Simulado Geral (edite à vontade; proporção aproximada da prova).
PESOS = {
    "Língua Portuguesa": 10,
    "Conhecimentos do DF e Legislação": 10,
    "SUAS": 10,
    "Programas e Benefícios do DF": 5,
    "Direito Constitucional": 5,
    "Direito Administrativo": 5,
    "Atendimento, Rotinas Administrativas e Arquivologia": 10,
    "Recursos Materiais, Patrimônio e Compras": 5,
}


def distribuir_por_peso(quantidade):
    """Divide a quantidade entre as matérias proporcionalmente aos PESOS."""
    total_pesos = sum(PESOS.values())
    exatas = {m: quantidade * p / total_pesos for m, p in PESOS.items()}
    dist = {m: int(v) for m, v in exatas.items()}
    sobra = quantidade - sum(dist.values())
    ordem = sorted(exatas, key=lambda m: exatas[m] - dist[m], reverse=True)
    for m in ordem[:sobra]:
        dist[m] += 1
    return dist
```

Ao final de `db.py`:

```python
def estatisticas(con):
    """Por matéria: total, inéditas, usadas e sem gabarito."""
    linhas = con.execute(
        "SELECT materia, COUNT(*) total,"
        " SUM(CASE WHEN usada_em_simulado=0 THEN 1 ELSE 0 END) ineditas,"
        " SUM(usada_em_simulado) usadas,"
        " SUM(CASE WHEN gabarito IS NULL THEN 1 ELSE 0 END) sem_gabarito"
        " FROM questoes GROUP BY materia ORDER BY materia").fetchall()
    return {l["materia"]: {"total": l["total"], "ineditas": l["ineditas"],
                           "usadas": l["usadas"], "sem_gabarito": l["sem_gabarito"]}
            for l in linhas}
```

- [ ] **Step 4: Rodar e ver passar** — suíte inteira: `..\.venv\Scripts\python.exe -m pytest -v`.

- [ ] **Step 5: Commit** — `git add banco_questoes && git commit -m "feat: pesos do edital, distribuicao proporcional e estatisticas"`

---

### Task 2: `gerar_completo` — Simulado Geral em PDF

**Files:**
- Modify: `banco_questoes\simulados\gerar_simulado.py` (acrescentar)
- Create: `banco_questoes\simulados\simulado_completo.py`
- Test: `banco_questoes\tests\test_gerar_simulado.py` (acrescentar)

**Interfaces:**
- Consumes: `edital.distribuir_por_peso`, `db.sortear_questoes`, `db.marcar_usadas`, estilos e `_capa`/`_origem` existentes do módulo.
- Produces: `gerar_completo(quantidade: int, arquivo_saida=None, con=None) -> Path | None` — seções por matéria com numeração contínua, capa "SIMULADO GERAL", gabarito comentado ao final; None + aviso se o banco estiver vazio; matérias sem questão suficiente entram com o que houver (aviso do `sortear_questoes` já cobre repetidas).

- [ ] **Step 1: Teste** — acrescentar em `tests\test_gerar_simulado.py`:

```python
def test_gerar_completo(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    materias = ["Língua Portuguesa", "SUAS", "Direito Administrativo"]
    n = 0
    for m in materias:
        for i in range(4):
            q = questao_fake(n); q["materia"] = m; q["id_qc"] = f"QG{n}"
            db.salvar_questao(con, q); n += 1
    saida = tmp_path / "geral.pdf"
    caminho = gerar_simulado.gerar_completo(12, saida, con=con)
    assert caminho == saida and saida.read_bytes()[:5] == b"%PDF-"
    usadas = con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"]
    assert usadas > 0


def test_gerar_completo_banco_vazio(tmp_path, capsys):
    con = db.conectar(tmp_path / "t.db")
    assert gerar_simulado.gerar_completo(10, tmp_path / "x.pdf", con=con) is None
    assert "Nenhuma questão" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar** — acrescentar em `gerar_simulado.py`:

```python
def gerar_completo(quantidade, arquivo_saida=None, con=None):
    """Simulado Geral: distribui a quantidade pelas matérias (edital.PESOS)."""
    import edital
    con_proprio = con is None
    if con_proprio:
        con = db.conectar()
    dist = edital.distribuir_por_peso(quantidade)
    blocos = []
    for materia, n in dist.items():
        if n <= 0:
            continue
        qs = db.sortear_questoes(con, materia, n)
        if qs:
            blocos.append((materia, qs))
    if not blocos:
        print("Nenhuma questão no banco ainda. Rode os coletores primeiro.")
        if con_proprio:
            con.close()
        return None

    total = sum(len(qs) for _, qs in blocos)
    if arquivo_saida is None:
        arquivo_saida = (Path(__file__).resolve().parent
                         / f"simulado_geral_{date.today():%Y%m%d}.pdf")
    arquivo_saida = Path(arquivo_saida)

    doc = SimpleDocTemplate(str(arquivo_saida), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Simulado Geral — SEDES/DF")
    story = [_capa("Simulado Geral", total), Spacer(1, 0.8 * cm)]
    numero = 0
    for materia, qs in blocos:
        story.append(Paragraph(escape(materia).upper(), e_num))
        for q in qs:
            numero += 1
            story.append(Paragraph(f"QUESTÃO {numero}", e_num))
            origem = _origem(q)
            if origem:
                story.append(Paragraph(escape(origem), e_origem))
            story.append(Paragraph(escape(q["enunciado"]), e_enunciado))
            for letra in sorted(q["alternativas"]):
                story.append(Paragraph(f"({letra}) {escape(q['alternativas'][letra])}", e_alt))
        story.append(Spacer(1, 0.5 * cm))

    story.append(PageBreak())
    story.append(Paragraph("GABARITO COMENTADO", e_num))
    numero = 0
    for materia, qs in blocos:
        for q in qs:
            numero += 1
            letra = q["gabarito"] or "— (gabarito ainda não coletado)"
            linha = f"<b>{numero}. {escape(letra)}</b>"
            if q.get("comentario"):
                linha += f" — {escape(q['comentario'])}"
            story.append(Paragraph(linha, e_gab))

    doc.build(story)
    for _, qs in blocos:
        db.marcar_usadas(con, [q["id"] for q in qs])
    print(f"Simulado Geral gerado: {arquivo_saida} ({total} questões)")
    if con_proprio:
        con.close()
    return arquivo_saida
```

Criar `simulados\simulado_completo.py`:

```python
r"""Gera o Simulado Geral. Rodar de banco_questoes\:
..\.venv\Scripts\python.exe -m simulados.simulado_completo 60"""
import sys

from simulados import gerar_simulado

quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 60
gerar_simulado.gerar_completo(quantidade)
```

- [ ] **Step 4: Rodar e ver passar** (suíte inteira).
- [ ] **Step 5: Commit** — `git commit -m "feat: simulado geral completo proporcional ao edital"`

---

### Task 3: `web_api.py` — API FastAPI

**Files:**
- Create: `banco_questoes\web_api.py`
- Test: `banco_questoes\tests\test_web_api.py`

**Interfaces:**
- Consumes: `db.estatisticas`, `db.zerar_usadas`, `gerar_simulado.gerar`, `gerar_simulado.gerar_completo`, `edital.nomes_materias`.
- Produces: app FastAPI `app` com rotas: `GET /api/stats`, `GET /api/materias`, `POST /api/simulado/materia` `{materia, quantidade}`, `POST /api/simulado/completo` `{quantidade}`, `GET /api/simulados` (lista PDFs), `GET /api/simulados/download/{nome}`, `POST /api/simulados/zerar`, `POST /api/coletar` + `GET /api/coletar/status`; monta `web/` como estático na raiz. Respeita `COLETA_DISPONIVEL` (env, default "1").

- [ ] **Step 1: Instalar deps** — `..\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" httpx`

- [ ] **Step 2: Testes** — `tests\test_web_api.py`:

```python
import db
import web_api
from fastapi.testclient import TestClient


def cliente_com_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "ARQUIVO_BANCO", tmp_path / "t.db")
    monkeypatch.setattr(web_api, "PASTA_SIMULADOS", tmp_path)
    return TestClient(web_api.app)


def test_stats_vazio(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.get("/api/stats")
    assert r.status_code == 200
    assert r.json() == {}


def test_materias(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    nomes = cliente.get("/api/materias").json()
    assert len(nomes) == 8 and "SUAS" in nomes


def test_simulado_materia_e_download(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar(tmp_path / "t.db")
    for i in range(3):
        db.salvar_questao(con, {
            "id_qc": f"QW{i}", "enunciado": f"Enunciado {i}?",
            "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            "gabarito": "A", "materia": "SUAS", "fonte": "qconcursos"})
    r = cliente.post("/api/simulado/materia", json={"materia": "SUAS", "quantidade": 3})
    assert r.status_code == 200
    nome = r.json()["arquivo"]
    assert nome.endswith(".pdf")
    baixado = cliente.get(f"/api/simulados/download/{nome}")
    assert baixado.status_code == 200
    assert baixado.content[:5] == b"%PDF-"


def test_simulado_materia_banco_vazio_da_404(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.post("/api/simulado/materia", json={"materia": "SUAS", "quantidade": 3})
    assert r.status_code == 404


def test_download_bloqueia_path_traversal(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.get("/api/simulados/download/..%2Fdb.py")
    assert r.status_code in (400, 404)


def test_zerar(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    assert cliente.post("/api/simulados/zerar").status_code == 200


def test_coletar_desabilitado(tmp_path, monkeypatch):
    monkeypatch.setattr(web_api, "COLETA_DISPONIVEL", False)
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.post("/api/coletar")
    assert r.status_code == 503
    assert "fora do Docker" in r.json()["detail"]
```

- [ ] **Step 3: Rodar e ver falhar.**

- [ ] **Step 4: Implementar `web_api.py`:**

```python
"""API web do banco de questões. Rodar: ..\\.venv\\Scripts\\python.exe -m uvicorn web_api:app --reload"""
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import edital
from simulados import gerar_simulado

PASTA = Path(__file__).resolve().parent
PASTA_SIMULADOS = PASTA / "simulados"
COLETA_DISPONIVEL = os.environ.get("COLETA_DISPONIVEL", "1") == "1"

app = FastAPI(title="Banco de Questões SEDES/DF")
_coleta = {"processo": None}


class PedidoMateria(BaseModel):
    materia: str
    quantidade: int = 20


class PedidoCompleto(BaseModel):
    quantidade: int = 60


@app.get("/api/stats")
def stats():
    con = db.conectar()
    est = db.estatisticas(con)
    con.close()
    return est


@app.get("/api/materias")
def materias():
    return edital.nomes_materias()


@app.post("/api/simulado/materia")
def simulado_materia(pedido: PedidoMateria):
    if pedido.materia not in edital.MATERIAS:
        raise HTTPException(400, "Matéria desconhecida.")
    con = db.conectar()
    caminho = gerar_simulado.gerar(pedido.materia, pedido.quantidade,
                                   PASTA_SIMULADOS / _nome_pdf(pedido.materia), con=con)
    con.close()
    if caminho is None:
        raise HTTPException(404, "Nenhuma questão dessa matéria no banco ainda.")
    return {"arquivo": caminho.name}


@app.post("/api/simulado/completo")
def simulado_completo(pedido: PedidoCompleto):
    con = db.conectar()
    caminho = gerar_simulado.gerar_completo(pedido.quantidade,
                                            PASTA_SIMULADOS / _nome_pdf("geral"), con=con)
    con.close()
    if caminho is None:
        raise HTTPException(404, "Nenhuma questão no banco ainda.")
    return {"arquivo": caminho.name}


def _nome_pdf(rotulo):
    from datetime import datetime
    limpo = rotulo.lower().replace(" ", "_").replace(",", "")
    return f"simulado_{limpo}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


@app.get("/api/simulados")
def listar_simulados():
    pdfs = sorted(PASTA_SIMULADOS.glob("*.pdf"), key=lambda p: p.stat().st_mtime,
                  reverse=True)
    return [p.name for p in pdfs]


@app.get("/api/simulados/download/{nome}")
def baixar_simulado(nome: str):
    if "/" in nome or "\\" in nome or ".." in nome or not nome.endswith(".pdf"):
        raise HTTPException(400, "Nome de arquivo inválido.")
    caminho = PASTA_SIMULADOS / nome
    if not caminho.exists():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(caminho, filename=nome, media_type="application/pdf")


@app.post("/api/simulados/zerar")
def zerar():
    con = db.conectar()
    db.zerar_usadas(con)
    con.close()
    return {"ok": True}


@app.post("/api/coletar")
def coletar():
    if not COLETA_DISPONIVEL:
        raise HTTPException(503, "Coleta indisponível aqui — rode fora do Docker,"
                                 " no Windows, onde o Chrome pode abrir.")
    if _coleta["processo"] is not None and _coleta["processo"].poll() is None:
        raise HTTPException(409, "Já existe uma coleta em andamento.")
    _coleta["processo"] = subprocess.Popen([sys.executable, str(PASTA / "scraper_qc.py")],
                                           cwd=PASTA)
    return {"ok": True, "mensagem": "Coleta iniciada — acompanhe pela janela do console."}


@app.get("/api/coletar/status")
def coleta_status():
    p = _coleta["processo"]
    if p is None:
        return {"rodando": False, "ultima_saida": None}
    codigo = p.poll()
    return {"rodando": codigo is None, "codigo_saida": codigo}


app.mount("/", StaticFiles(directory=PASTA / "web", html=True), name="web")
```

Criar também a pasta `banco_questoes\web\` com um `index.html` mínimo provisório (`<h1>Dashboard em construção</h1>`) para o mount não falhar — a Task 4 substitui.

- [ ] **Step 5: Rodar e ver passar** (suíte inteira).
- [ ] **Step 6: Commit** — `git commit -m "feat: API web FastAPI do banco de questoes"`

---

### Task 4: `web/index.html` — Dashboard

**Files:**
- Create: `banco_questoes\web\index.html` (substitui o provisório; único arquivo, CSS/JS inline)

**Interfaces:**
- Consumes: todas as rotas da Task 3 via `fetch` (mesma origem).

- [ ] **Step 1: Implementar o dashboard** — página única, sem framework, PT-BR, com:
  1. **Cards de estatísticas** (`GET /api/stats`): por matéria — total, inéditas, usadas, sem gabarito; barra de proporção inéditas/usadas; card de total geral.
  2. **Gerar simulado por matéria**: `<select>` populado por `GET /api/materias` + campo quantidade (padrão 20) + botão → `POST /api/simulado/materia`; ao concluir, atualiza a lista de downloads e abre o PDF.
  3. **Gerar Simulado Geral**: campo quantidade (padrão 60) + botão → `POST /api/simulado/completo`.
  4. **Central de downloads** (`GET /api/simulados`): lista com links `GET /api/simulados/download/{nome}`.
  5. **Botão Coletar questões** → `POST /api/coletar`; se 503, mostra o aviso e desabilita; enquanto `GET /api/coletar/status` retornar `rodando: true`, mostra "coletando…" (poll a cada 5 s).
  6. **Botão Zerar histórico** com `confirm()` antes de `POST /api/simulados/zerar`.
  Estilo: fundo claro, cartões com sombra leve, azul `#1B3A6B` como cor primária (mesma dos PDFs), responsivo (grid que quebra em telas estreitas), mensagens de erro visíveis em vermelho.

- [ ] **Step 2: Teste manual** — subir `..\.venv\Scripts\python.exe -m uvicorn web_api:app` e conferir no navegador: stats aparecem, gerar simulado funciona com banco populado (ou mostra o erro claro com banco vazio), download baixa o PDF.

- [ ] **Step 3: Commit** — `git commit -m "feat: dashboard web do banco de questoes"`

---

### Task 5: Docker

**Files:**
- Create: `c:\Users\Felps\Documents\training\Dockerfile`
- Create: `c:\Users\Felps\Documents\training\docker-compose.yml`
- Modify: `c:\Users\Felps\Documents\training\.gitignore` (garantir `perfil_chrome_scraper/`)

**Interfaces:**
- Consumes: `web_api:app` da Task 3.
- Produces: `docker compose up` → dashboard em `http://localhost:8000` com coleta desabilitada; banco e PDFs persistem no host via bind mount.

- [ ] **Step 1: `Dockerfile`:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" reportlab requests \
    beautifulsoup4 pdfplumber
ENV COLETA_DISPONIVEL=0
EXPOSE 8000
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: `docker-compose.yml`:**

```yaml
services:
  banco-questoes:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./banco_questoes:/app
    environment:
      - COLETA_DISPONIVEL=0
```

(O bind mount entrega código + banco + PDFs; a imagem só carrega as dependências. `selenium` fica de fora da imagem de propósito.)

- [ ] **Step 3: Testar** — `docker compose up --build` na raiz `training/`; abrir `http://localhost:8000`; conferir: stats ok, gerar/baixar simulado ok, botão de coleta desabilitado com aviso. Se o Docker Desktop não estiver instalado/rodando, registrar a pendência e concluir com os arquivos prontos.

- [ ] **Step 4: Commit** — `git commit -m "feat: dockerfile e compose para o dashboard web"`

---

## Rotina depois da Fase 2

- **No Windows (com coleta):** `..\.venv\Scripts\python.exe -m uvicorn web_api:app` → `http://localhost:8000`.
- **Via Docker (sem coleta):** `docker compose up` na raiz `training/`.
- Coleta continua também disponível por CLI: `scraper_qc.py` / `scraper_qc.py gabaritos` / `coletor_quadrix.py`.
