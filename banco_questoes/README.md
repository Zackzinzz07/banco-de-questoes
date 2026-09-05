# Banco de Questões de Concursos Públicos

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green.svg)](https://fastapi.tiangolo.com/)
[![Testes](https://img.shields.io/badge/testes-325-success.svg)](#testes)

Coleta, classifica e gera simulados em PDF de questões de concursos públicos
brasileiros. O objetivo é **multi-concurso**: um acervo único do qual se monta a
prova de qualquer edital, não um sistema amarrado a um concurso específico.

---

## O acervo hoje

```
118.319 questões          51 matérias · 486 bancas · 2.416 órgãos

  PCI Concursos    101.352    gabarito 100%
  QConcursos        16.600    cargo 95,5%
  Quadrix (PDF)        367    gabarito 100%
```

Mais um arquivo de provas oficiais da Cebraspe, em construção:

```
162 concursos · 3.826 PDFs · 958 MB
cadernos, gabaritos definitivos e editais de abertura
```

As fontes são complementares, não redundantes: o PCI publica o gabarito junto
da questão; o QConcursos identifica o cargo mas cobra o gabarito por questão
respondida; a Cebraspe entrega prova, gabarito oficial e, em parte dos
certames, a **justificativa da própria banca** item a item.

---

## O que dá para fazer

### Simulado com a forma de um edital

Monta uma prova com o mesmo número de questões e a mesma proporção de matérias
que um edital cobra, usando questões de qualquer banca do acervo.

```python
import db
from simulados import por_edital
import edital_loader

con = db.conectar()
pesos = edital_loader.obter_pesos("pmdf", "Soldado Policial Militar")
simulado = por_edital.montar(con, pesos)

print(len(simulado.questoes))   # 89
print(simulado.lacunas)         # {'Língua Inglesa': 5, ...}
print(simulado.completo)        # False
```

O ponto central: quando falta conteúdo para uma matéria, ele **declara a
lacuna** em vez de completar com questão de outro assunto. Um simulado de 89
questões certas com aviso vale mais que 120 com 31 erradas.

### Simulado em PDF no estilo de cada banca

```bash
.venv/bin/python -m simulados.cli_multibanca --banca cebraspe --quantidade 120
.venv/bin/python -m simulados.cli_multibanca --banca iades --quantidade 60
```

Seis estilos implementados (`simulados/estilos/`), com layout, fonte, colunas
e formato de resposta próprios de cada banca.

### API web e painel

```bash
.venv/bin/python -m uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
```

Dezoito rotas HTTP: estatísticas do acervo, geração de simulado por matéria,
por cargo ou completo, e download dos PDFs gerados.

---

## Coletores

| Fonte | Comando | Transporte | Escopo |
|---|---|---|---|
| PCI Concursos | `python -m scrapers.pci.coletor_v2` | HTTP | 41 categorias |
| QConcursos | `python coletar_qc.py` | Playwright | 254 disciplinas |
| Cebraspe | `python coletar_cebraspe.py` | HTTP | 425 concursos |

Todos salvam progresso a cada página e **retomam de onde pararam**. O da
Cebraspe interrompe sozinho se o disco livre cair abaixo de 5 GB.

O acompanhamento sai do próprio banco, não do log:

```bash
.venv/bin/python -m scripts.status --materia
.venv/bin/python -m scripts.status --vivo      # atualiza a cada 15s
```

### Sobre o QConcursos

O catálogo de 267 disciplinas foi levantado por dois agentes independentes na
interface logada; 244 IDs coincidiram nos dois com nome idêntico. Dez ficaram
de fora por devolverem 2.657.288 questões — o acervo inteiro do site, sinal de
que o filtro não aplica.

O gabarito **não** é coletado junto do enunciado: o QC só o revela ao responder
a questão, e cada resposta consome cota diária da conta. É a razão de o campo
vir vazio nessa fonte.

---

## Arquitetura

Quatro camadas, com fronteiras verificadas por hooks de git em vez de boa
vontade (ver [`CLAUDE.md`](CLAUDE.md)):

```
automação    scraper_qc.py, scrapers/*/coletor*.py
             só rede: Playwright ou HTTP. Proibido BeautifulSoup, proibido banco.

parsing      scrapers/*/parser.py, scrapers/cebraspe/leitura_pdf.py
             funções puras: recebem HTML ou bytes, devolvem modelos. Sem I/O.

persistência db.py, sanitizacao.py, migrations/
             queries e gravação. Proibido seletor de DOM.

orquestração coletar_qc.py, coletar_cebraspe.py, simulados/
             abre navegador e conexão, passa adiante, fecha em try/finally.
```

A tradução entre vocabulários fica em [`taxonomia.py`](taxonomia.py), fora das
camadas: o edital escreve *"Noções de Direito Administrativo"*, o banco guarda
*"Direito Administrativo"*, e sem tradução 9 das 10 matérias de um edital
devolvem zero. Ela tem um **guardrail** que impede *Direito Penal Militar* de
casar com *Direito Penal* — são ramos distintos, e uma questão trocada num
simulado corrói a confiança mais do que uma questão a menos.

---

## Instalação

Requisitos: Python 3.10+, PostgreSQL 14+, Google Chrome (para o coletor do QC).

```bash
git clone <repo> && cd banco_questoes
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

cp .env.example .env          # ajuste DATABASE_URL
.venv/bin/python -c "import db; db.conectar()"   # cria tabelas e migrations
```

O coletor do QConcursos precisa de login. Ele usa um perfil dedicado do Chrome
(`perfil_chrome_scraper/`, nunca versionado), populado uma vez com
`salvar_html_exemplo.py`. Roda com janela visível de propósito: o Cloudflare do
site bloqueia navegador invisível.

---

## Banco de dados

Tabela `questoes`, com deduplicação em duas camadas:

- `hash_enunciado` — impede o mesmo enunciado literal de entrar duas vezes
- `content_hash` — impede a mesma questão vinda de fontes diferentes

`progresso_scraper` guarda a última página coletada por fonte e chave, e é o
que permite parar e retomar sem reprocessar.

---

## Configuração por concurso

Nove editais descritos em YAML, em `configuracoes_editais/`: BACEN, Banco do
Brasil, Correios, INSS, PCDF, PMDF, PRF, Receita Federal e SEDES/DF. Cada um
lista cargos e, por cargo, quantas questões de cada matéria a prova cobra.

Concurso é **dado, não código**: adicionar um concurso é escrever um YAML, não
um script.

Em `configuracoes_bancas/` ficam os estilos visuais (Cebraspe, FGV, IADES,
AOCP) usados na geração de PDF.

---

## Testes

```bash
.venv/bin/python -m pytest -q
```

325 testes. Os que tocam banco são redirecionados para um banco de teste
separado por uma fixture `autouse` — houve um episódio em que testes gravaram
em produção, e a fixture não tem exceção por arquivo desde então.

---

## Estado atual e limitações

**O que funciona:** coleta das três fontes com retomada; geração de PDF em seis
estilos de banca; simulado com a forma de um edital; API e painel web.

**O que está em construção:**

- As questões da Cebraspe estão arquivadas e extraídas em JSON, mas **ainda não
  entram na tabela `questoes`**. O caderno identifica só o bloco da prova
  (*"Conhecimentos Básicos"*), nunca a matéria, e gravar o bloco como se fosse
  matéria contaminaria o sorteio. A vinculação depende do mapa de faixas de
  itens de cada prova.
- O QConcursos coleta enunciado sem gabarito. A segunda fase
  (`python coletar_qc.py gabaritos`) resolve, mas consome cota diária.
- Três matérias do PMDF seguem sem fonte: `Língua Inglesa` e
  `Direitos Humanos e Criminologia` existem no catálogo do QC e entram quando a
  coleta chegar nelas; `Legislação Específica da PMDF` só existe no arquivo do
  Instituto AOCP, que ainda não tem coletor.
- `Informática` (nome do PCI) e `Noções de Informática` (nome do QC) convivem
  como matérias distintas no banco. A taxonomia resolve as duas ao montar o
  simulado, mas a contagem por matéria fica dividida.
