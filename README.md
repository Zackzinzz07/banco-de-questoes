# Banco de Questões de Concursos Públicos

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green.svg)](https://fastapi.tiangolo.com/)
[![Testes](https://img.shields.io/badge/testes-351-success.svg)](#testes)

Coleta, classifica e gera simulados em PDF de questões de concursos públicos
brasileiros. O objetivo é **multi-concurso**: um acervo único do qual se monta a
prova de qualquer edital, não um sistema amarrado a um concurso específico.

O código do projeto vive em [`banco_questoes/`](banco_questoes/); este README
descreve o projeto inteiro e é a página que o GitHub mostra na raiz.

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

print(len(simulado.questoes))   # 65
print(simulado.lacunas)         # {'Legislação Aplicável a Polícia Militar do Distrito Federal': 10, ...}
print(simulado.completo)        # False
```

O ponto central: quando falta conteúdo para uma matéria, ele **declara a
lacuna** em vez de completar com questão de outro assunto. Um simulado menor
com aviso vale mais que um maior com questão errada no meio.

### Simulado em PDF por formato de prova ou por banca

```bash
.venv/bin/python -m simulados.cli_multibanca --banca multipla_escolha --concurso pmdf --quantidade 80
.venv/bin/python -m simulados.cli_multibanca --banca certo_errado --concurso prf --quantidade 120
```

O motor universal (`simulados/estilos/universal.py`) organiza o simulado pelo
**formato da prova** — múltipla escolha ou certo/errado — em vez de travar numa
banca específica, já que a maior parte do acervo é múltipla escolha
independente de quem organizou a prova original. Os quatro estilos visuais por
banca (Cebraspe, AOCP, FGV, IADES) continuam disponíveis para quem quer o
layout de uma banca específica.

### API web e painel

```bash
.venv/bin/python -m uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
```

Estatísticas do acervo, geração de simulado por matéria, por cargo/edital ou
por formato de prova, e download dos PDFs gerados.

---

## Coletores

| Fonte | Comando | Transporte | Escopo |
|---|---|---|---|
| PCI Concursos | `python -m scrapers.pci.coletor_v2` | HTTP | 41 categorias |
| QConcursos | `python coletar_qc.py` | Playwright | 254 disciplinas |
| Cebraspe | `python coletar_cebraspe.py` | HTTP | 425 concursos |
| AOCP | `python coletar_aocp.py` | Playwright | em coleta |
| IADES | via `scrapers/iades/` | Playwright | em coleta |

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
vontade (ver [`banco_questoes/CLAUDE.md`](banco_questoes/CLAUDE.md)):

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

A tradução entre vocabulários fica em
[`taxonomia.py`](banco_questoes/taxonomia.py), fora das camadas: o edital
escreve *"Português"* ou *"Noções de Direito Administrativo"*, o banco guarda
*"Língua Portuguesa"* e *"Direito Administrativo"*, e sem tradução a maioria
das matérias de um edital devolve zero. Ela tem um **guardrail** que impede
*Direito Penal Militar* de casar com *Direito Penal* — são ramos distintos, e
uma questão trocada num simulado corrói a confiança mais do que uma questão a
menos.

---

## Instalação

Requisitos: Python 3.10+, PostgreSQL 14+, Google Chrome (para o coletor do QC).

```bash
git clone <repo> && cd banco-de-questoes/banco_questoes
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

Nove editais descritos em YAML, em
[`configuracoes_editais/`](banco_questoes/configuracoes_editais/): BACEN,
Banco do Brasil, Correios, INSS, PCDF, PMDF, PRF, Receita Federal e SEDES/DF.
Cada um lista cargos e, por cargo, quantas questões de cada matéria a prova
cobra — sempre a partir do edital oficial publicado, nunca de estimativa (ver
a regra em [`CLAUDE.md`](banco_questoes/CLAUDE.md)). Quando o edital detalha o
conteúdo programático de cada matéria, ele fica num arquivo
`<concurso>_<cargo>_conteudo_programatico.yaml` ao lado do principal.

Concurso é **dado, não código**: adicionar um concurso é escrever um YAML, não
um script.

Em [`configuracoes_bancas/`](banco_questoes/configuracoes_bancas/) ficam os
estilos visuais (Cebraspe, FGV, IADES, AOCP) usados na geração de PDF.

---

## Testes

```bash
.venv/bin/python -m pytest -q
```

351 testes. Os que tocam banco são redirecionados para um banco de teste
separado por uma fixture `autouse` — houve um episódio em que testes gravaram
em produção, e a fixture não tem exceção por arquivo desde então.

---

## Estado atual e limitações

**O que funciona:** coleta das cinco fontes com retomada; geração de PDF por
formato de prova ou por estilo de banca; simulado com a forma de um edital;
API e painel web.

**O que está em construção:**

- As questões da Cebraspe estão arquivadas e sendo importadas para a tabela
  `questoes` (`scripts/importar_cebraspe.py`), mas ainda cobrem uma fração
  pequena do acervo — a maior parte das questões em formato certo/errado do
  banco ainda vem de outras fontes reclassificadas, não da Cebraspe original.
- O QConcursos coleta enunciado sem gabarito. A segunda fase
  (`python coletar_qc.py gabaritos`) resolve, mas consome cota diária.
- Cada concurso em `configuracoes_editais/` tem matérias que existem só no
  edital oficial e ainda não têm fonte no acervo (ex.: legislação bem
  específica de um órgão, ou conteúdo de nicho como Criminologia) — o gerador
  declara a lacuna em vez de inventar, mas fechar esses buracos depende de
  coleta nova, não de código.
- `Informática` (nome do PCI) e `Noções de Informática` (nome do QC) convivem
  como matérias distintas no banco. A taxonomia resolve as duas ao montar o
  simulado, mas a contagem por matéria fica dividida.

---

<sub>Os números acima (acervo, testes) vivem só neste arquivo — evita a
divergência que já aconteceu antes, com a home do GitHub mostrando "19.721
questões" enquanto o projeto já passava de 116 mil.</sub>
