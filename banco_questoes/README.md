# 📚 Banco de Questões de Concursos Públicos

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-orange.svg)](https://playwright.dev/)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF-red.svg)](https://www.reportlab.com/)
[![Status](https://img.shields.io/badge/Status-Ativo%20%2F%20Produção-success.svg)](#)

Sistema de alta performance para **coleta**, **taxonomia**, **armazenamento**, **análise** e **geração de simulados em PDF** para concursos públicos. Atualmente o acervo conta com **mais de 116.700 questões** catalogadas no PostgreSQL (*PCI Concursos*, *QConcursos* e *Quadrix*), além de um pipeline com **mais de 160 concursos oficiais da Cebraspe** arquivados em PDF com cadernos e gabaritos definitivos,futuramnte com todos os concursos e bancas do  brasil.

---

## 📋 Sumário

- [🎯 Visão Geral](#-visão-geral)
- [✨ Principais Funcionalidades](#-principais-funcionalidades)
- [🔍 Mapeamento Autônomo e Catálogo QC](#-mapeamento-autônomo-e-catálogo-qc)
- [📐 Arquitetura e Separação de Camadas](#-arquitetura-e-separação-de-camadas)
- [📂 Estrutura do Projeto](#-estrutura-do-projeto)
- [🗄️ Banco de Dados & Deduplicação](#️-banco-de-dados--deduplicação)
- [📄 Motor Multi-Banca de Simulados PDF](#-motor-multi-banca-de-simulados-pdf)
- [🌐 API Web e Dashboard Educacional](#-api-web-e-dashboard-educacional)
- [⚙️ Guia de Instalação e Execução](#️-guia-de-instalação-e-execução)
- [🧪 Testes Automatizados e Qualidade](#-testes-automatizados-e-qualidade)

---

## 🎯 Visão Geral

O projeto automatiza o ciclo de vida completo do estudo para concursos públicos:
1. **Scraping Multi-Fonte**: Extração automatizada e ética de questões respeitando cotas, sessões e contornando desafios anti-bot (Cloudflare Turnstile) via Playwright no QConcursos, requisições com parser BeautifulSoup no PCI Concursos e leitor de cadernos oficiais da Cebraspe em PDF.
2. **Normalização e Taxonomia**: Mapeamento inteligente de conteúdos por órgão, banca, cargo, ano, disciplina, categoria e tema, resolvendo discrepâncias de nomenclaturas entre editais e fontes via guardrails rigorosos (`taxonomia.py` e `conteudo_mapper.py`).
3. **Deduplicação Rigorosa e Sanitização**: Algoritmos baseados em hash MD5 (`content_hash`) e SHA256 (`hash_enunciado`) para evitar duplicatas entre fontes distintas, acompanhados de sanitização de caracteres nulos (`\x00`) para conformidade com PostgreSQL (`sanitizacao.py`).
4. **Exportação Editorial em PDF**: Geração de cadernos de simulados diagramados em 2 colunas com layout e tipografia fiéis aos das bancas oficiais (**Cebraspe**, **IADES**, **FGV**, **AOCP** no motor multi-banca e **Quadrix** no gerador dedicado SEDES/DF).
5. **Dashboard Interativo**: Interface web em FastAPI para acompanhar estatísticas por disciplina, cargo e concurso, status dos scrapers e download direto dos PDFs gerados.

### Concursos Suportados por Edital (YAML)

O sistema possui especificações prontas para editais de concursos estratégicos em `configuracoes_editais/`:
* **SEDES/DF** (Secretaria de Desenvolvimento Social do DF)
* **PMDF** (Polícia Militar do DF)
* **PCDF** (Polícia Civil do DF)
* **BACEN** (Banco Central do Brasil)
* **INSS** (Instituto Nacional do Seguro Social)
* **PRF** (Polícia Rodoviária Federal)
* **Receita Federal** (RFB)
* **Correios** (Empresa Brasileira de Correios e Telégrafos)
* **Banco do Brasil** (BB)

---

## ✨ Principais Funcionalidades

- **Coleta Multi-Fonte Especializada**:
  - `QConcursos`: Coleta via Playwright com perfil persistente logado (`perfil_chrome_scraper`), catálogo integrado de mais de 230 disciplinas ativas e controle de cota diária com resolução automatizada para captura de gabaritos (`coletar_qc.py gabaritos`).
  - `PCI Concursos`: Coleta com hierarquia completa (`categoria` e `tema`), suporte a texto associado e persistência de imagens de apoio em formato JSONB.
  - `Cebraspe PDF`: Pipeline de download e arquivamento de editais, cadernos de prova e gabaritos definitivos com leitura em duas colunas e identificação de anulações/alterações em `provas_pdf/cebraspe/`.
- **Deduplicação por `content_hash`**: Garante que a mesma questão vinda de fontes distintas não seja gravada duas vezes no PostgreSQL.
- **Gerador Multi-Banca & SEDES**: Engine baseada em ReportLab (Canvas e Platypus) que desenha cadernos profissionais de simulados com folhas de gabarito.
- **Dashboard Educacional**: Interface visual web (estilo gamificado/Duolingo) com estatísticas detalhadas por matéria, cobertura de edital, inéditas vs. usadas e download direto dos PDFs.

---

## 🔍 Mapeamento Autônomo e Catálogo QC

Para expandir a cobertura do coletor do QConcursos além do escopo inicial de 23 disciplinas, foi realizada uma varredura automatizada (`scripts/mapear_disciplinas_qc.py`) no intervalo de IDs 1 a 600+ utilizando Playwright com perfil logado.

### Resultados e Integração:
- **Disciplinas Auditadas**: Catálogo de IDs 1 a 623 verificado por múltiplos agentes independentes.
- **Disciplinas Ativas**: **244 disciplinas ativas catalogadas** (mais de 1,8 milhão de questões mapeadas no QConcursos).
- **Catálogo Integrado (`scrapers/qc/catalogo.py`)**: Mais de 230 disciplinas integradas nativamente ao registro de coleta (`scrapers/qc/disciplinas.py`), com expurgo e bloqueio de 10 IDs com contagem falsa (IDs de disciplinas globais ou inválidas como 52, 197, 209, etc.).
- **Persistência dos Dados de Auditoria**:
  - `estudo_autonomo/mapeamento_disciplinas_qc.json`: Estrutura JSON completa com ID, Nome, Quantidade de questões e Status.
  - `estudo_autonomo/mapeamento_disciplinas_qc.csv`: Planilha formatada para auditoria e conferência.

---

## 📐 Arquitetura e Separação de Camadas

O projeto adota **Arquitetura Limpa em 5 Camadas**, com limites estritos de tamanho de arquivo fiscalizados por diretrizes de lint (ver [CLAUDE.md](CLAUDE.md)):

```
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Orquestração                   │
│ (coletar_qc.py, coletar_cebraspe.py, cli_multibanca.py)     │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼──────────────┐
│    Camada de Automação      ││    Camada de Persistência   │
│  (Playwright / HTTP pure)   ││   (db.py / PostgreSQL)      │
│   [Sem BeautifulSoup/DB]    ││     [Sem DOM/Parsing]       │
└──────────────┬──────────────┘└──────────────────────────────┘
               │
┌──────────────▼──────────────┐
│      Camada de Parsing      │
│  (scrapers/*/parser.py)     │
│  [Funções 100% Puras/BS4]   │
└─────────────────────────────┘
```

1. **Automação** (`scraper_qc.py`, `scrapers/http_utils.py`): Navegação HTTP/Playwright e captura de HTML bruto. Sem BeautifulSoup e sem acesso direto a banco de dados.
2. **Parsing** (`scrapers/*/parser.py`, `leitura_pdf.py`): Extração de dados usando BeautifulSoup ou pdfplumber. Funções puras que recebem HTML/bytes e devolvem modelos tipados.
3. **Modelos e Taxonomia** (`taxonomia.py`, `conteudo_mapper.py`): Contratos da questão, guardrails contra fusões indevidas de matérias e categorização.
4. **Persistência e Sanitização** (`db.py`, `sanitizacao.py`, `migrations/`): Conexões PostgreSQL, queries SQL, deduplicação por hash, controle de progresso e sanitização de strings.
5. **Orquestração** (`coletar_qc.py`, `coletar_cebraspe.py`, `web_api.py`, `simulados/cli_multibanca.py`): Coordenação dos fluxos lendo da automação, passando pelo parser e gravando na persistência em blocos seguros `try...finally`.

---

## 📂 Estrutura do Projeto

```
banco_questoes/
├── CLAUDE.md                       # Diretrizes de desenvolvimento e limites de código
├── README.md                       # Documentação principal do projeto
├── requirements.txt                # Dependências do projeto Python
├── config.py                       # Configurações de ambiente e URLs do banco de dados
├── db.py                           # Camada de persistência PostgreSQL e deduplicação
├── sanitizacao.py                  # Sanitização de caracteres nulos (\x00) e textos
├── taxonomia.py                    # Normalização e guardrails de disciplinas
├── conteudo_mapper.py              # Mapeador unificado de Matéria → Categoria → Tema
├── mapeamento_conteudos.yaml       # Base hierárquica de temas e categorias
├── edital.py                       # Registro legado de disciplinas e pesos do SEDES/DF
├── edital_loader.py                # Carregador YAML multi-concurso (editais dinâmicos)
├── web_api.py                      # Servidor REST API em FastAPI
├── coletar_qc.py                   # Orquestrador de coleta do QConcursos
├── coletar_cebraspe.py             # Orquestrador de arquivamento e extração Cebraspe PDF
├── scraper_qc.py                   # Automação de navegador Playwright para o QC
│
├── configuracoes_bancas/           # Especificações YAML das bancas examinadoras
│   ├── cebraspe.yaml
│   ├── iades.yaml
│   ├── fgv.yaml
│   └── aocp.yaml
│
├── configuracoes_editais/          # Especificações YAML dos editais por concurso
│   ├── sedes_df.yaml
│   ├── pmdf.yaml
│   ├── pcdf.yaml
│   ├── bacen.yaml
│   ├── inss.yaml
│   ├── prf.yaml
│   ├── receita_federal.yaml
│   ├── correios.yaml
│   └── banco_brasil.yaml
│
├── estudo_autonomo/                # Resultados de análises, mapeamentos e simulados gerados
│   ├── mapeamento_disciplinas_qc.json
│   └── mapeamento_disciplinas_qc.csv
│
├── scrapers/                       # Módulos de scraping por fonte
│   ├── http_utils.py               # Sessões HTTP, retries e rate limiting
│   ├── qc/                         # Parser, disciplinas e catálogo do QConcursos
│   │   ├── catalogo.py
│   │   ├── disciplinas.py
│   │   └── parser.py
│   ├── pci/                        # Coletor e parser do PCI Concursos
│   │   ├── coletor_v2.py
│   │   ├── config.py
│   │   └── parser.py
│   └── cebraspe/                   # Leitor de provas e gabaritos oficiais em PDF
│       ├── coletor.py
│       ├── config.py
│       ├── leitura_pdf.py
│       └── parser.py
│
├── simulados/                      # Engine de geração de simulados em PDF
│   ├── cli_multibanca.py           # CLI oficial multi-banca via Click
│   ├── gerador_multibanca.py       # Motor ReportLab Canvas para bancas suportadas
│   ├── gerar_simulado.py           # Gerador ReportLab Platypus legado (SEDES/Quadrix)
│   └── estilos/                    # Implementações visuais por banca
│       ├── base.py
│       ├── cebraspe.py
│       ├── iades.py
│       ├── fgv.py
│       ├── aocp.py
│       └── alternativas.py
│
├── scripts/                        # Scripts de automação, varredura e manutenção
│   ├── mapear_disciplinas_qc.py    # Varredura de IDs no QConcursos
│   ├── gerar_simulado_pmdf.py      # Gerador de simulado para PMDF
│   ├── importar_sqlite.py          # Importador de banco SQLite legado para PostgreSQL
│   └── status.py                   # Panorama em tempo real do acervo no banco
│
├── tests/                          # Suíte de testes automatizados (pytest - 300+ testes)
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_disciplinas_qc.py
│   ├── test_gerador_multibanca.py
│   ├── test_web_api.py
│   └── ...
│
└── web/                            # Frontend estático e Dashboards
    ├── dashboard_educacional.html  # Dashboard principal gamificado
    ├── dashboard.html              # Dashboard geral com gráficos
    ├── dashboard_materia.html      # Visão detalhada por matéria
    ├── dashboard_pci.html          # Visão de cobertura do PCI Concursos
    ├── debug.html                  # Interface de diagnóstico
    ├── index.html
    ├── script.js
    └── style.css
```

---

## 🗄️ Banco de Dados & Deduplicação

O projeto utiliza **PostgreSQL** com cursores tipados (`RealDictCursor`).

### Esquema Principal (`questoes`)

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identificador único interno |
| `id_qc` | `TEXT UNIQUE` | ID original no QConcursos (quando aplicável) |
| `enunciado` | `TEXT NOT NULL` | Texto do enunciado da questão |
| `hash_enunciado` | `TEXT UNIQUE NOT NULL` | SHA256 do enunciado normalizado |
| `content_hash` | `TEXT` *(Indexado)* | MD5 de `normalizar(enunciado) + json(alternativas)` para dedupe |
| `alternativas` | `TEXT NOT NULL` | JSON contendo o dicionário/lista de alternativas |
| `gabarito` | `TEXT` | Alternativa correta (ex: "A", "Certo", "Errado") |
| `comentario` | `TEXT` | Comentário ou explicação da resolução |
| `materia` | `TEXT NOT NULL` | Nome normalizado da disciplina |
| `assunto` | `TEXT` | Sub-tópico ou assunto da questão |
| `ano` | `INTEGER` | Ano da aplicação da prova |
| `prova` | `TEXT` | Nome do concurso/órgão da prova original |
| `fonte` | `TEXT NOT NULL` | Origem da questão (`qconcursos`, `pci`, `quadrix_pdf`) |
| `usada_em_simulado` | `INTEGER NOT NULL DEFAULT 0` | Controle de ineditismo (0 = virgem, 1 = usada) |
| `texto_associado` | `TEXT` | Texto-base ou contexto compartilhado da questão |
| `imagens` | `TEXT` | JSON com lista de imagens de apoio locais |
| `categoria` | `VARCHAR(255)` | Categoria macro da taxonomia |
| `tema` | `VARCHAR(255)` | Tema específico da taxonomia |
| `imagens_urls` | `JSONB DEFAULT '[]'` | URLs das imagens originais de apoio |
| `banca` | `TEXT` | Nome oficial da banca examinadora |
| `orgao` | `TEXT` | Órgão contratante do concurso |
| `cargo` | `TEXT` | Cargo público correspondente |

### Tabela de Controle de Progresso (`progresso_scraper`)

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `fonte` | `TEXT NOT NULL` | Identificador do scraper (`pci`, `qconcursos`) |
| `chave` | `TEXT NOT NULL` | Categoria/tema ou disciplina que foi rastreada |
| `ultima_pagina` | `INTEGER NOT NULL` | Última página concluída com sucesso para retomada |

*Chave primária composta: `(fonte, chave)`.*

### Deduplicação Automática

Antes de qualquer inserção, o sistema calcula o `content_hash`:
```python
content_hash = md5(normalizar(enunciado) + "|" + json.dumps(sorted_alternativas))
```
Se a mesma questão for extraída via PCI Concursos e via QConcursos, o banco rejeita a duplicata transparentemente por conferência prévia do hash no banco ou violação de integridade.

---

## 📄 Motor Multi-Banca de Simulados PDF

O projeto dispõe de duas abordagens complementares para geração de cadernos em formato PDF:

### 1. Motor Multi-Banca (`simulados/gerador_multibanca.py`):
Engine que desenha diretamente no Canvas do ReportLab, respeitando as características visuais específicas de quatro grandes organizadoras:
* **Cebraspe**: Questões no formato **Certo/Errado (C/E)**, 2 colunas com divisor contínuo, cabeçalho e numeração de página no rodapé (`- 1 -`).
* **IADES**: Questões de **Múltipla Escolha (A-E)**, 2 colunas sem divisor e tipografia Calibri/Arial.
* **FGV**: Enunciados extensos de análise jurisprudencial/casos em 2 colunas com divisor fino cinza.
* **AOCP**: Múltipla escolha objetiva com diagramação limpa em 2 colunas.

> **Nota sobre Quadrix**: A banca **Instituto Quadrix** não integra o motor multi-banca abstrato; ela é atendida pelo gerador dedicado do concurso SEDES/DF ([simulados/gerar_simulado.py](simulados/gerar_simulado.py)).

### Como Gerar um Simulado via CLI:

```bash
# Simulado Cebraspe com 120 questões (C/E)
python -m simulados.cli_multibanca --banca cebraspe --quantidade 120 --nome simulado_cebraspe.pdf

# Simulado IADES com 60 questões (Múltipla Escolha)
python -m simulados.cli_multibanca --banca iades --quantidade 60 --nome simulado_iades.pdf

# Simulado filtrando órgão ou banca original das questões
python -m simulados.cli_multibanca --banca cebraspe --quantidade 60 --orgao "PRF"

# Simulado completo para o concurso da PMDF (Soldado)
python scripts/gerar_simulado_pmdf.py
```

---

## 🌐 API Web e Dashboard Educacional

A aplicação possui uma REST API desenvolvida em **FastAPI** (`web_api.py`) integrada a um dashboard estático.

### Iniciar o Servidor API:

```bash
# Executar localmente na porta 8000
python -m uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
```
Acesse o Dashboard no navegador: `http://localhost:8000` (redireciona para `/dashboard_educacional.html`).

### Principais Endpoints HTTP:

* **`GET /api/stats`**: Resumo das estatísticas de questões (total, inéditas, usadas e sem gabarito por matéria).
* **`GET /api/stats/todas`**: Distribuição global de questões por órgão e matéria.
* **`GET /api/stats/materias`**: Resumo de matérias únicas, fontes e amostra de categorias.
* **`GET /api/materias`**: Lista os nomes de disciplinas configuradas no edital base.
* **`GET /api/orgaos`**: Lista todos os órgãos e concursos configurados em YAML.
* **`GET /api/cargos/{orgao}`**: Lista os cargos disponíveis para o órgão selecionado.
* **`GET /api/materias/{orgao}/{cargo}`**: Matérias e distribuição de pesos para o cargo.
* **`GET /api/stats/cargo/{orgao}/{cargo}`**: Cobertura percentual de questões no banco para o edital do cargo.
* **`GET /api/pci/status`**: Panorama do acervo do PCI Concursos com top categorias.
* **`GET /api/stats/pci`**: Estatísticas completas do PCI divididas por categoria e tema.
* **`GET /api/stats/pci/{categoria}`**: Detalhes e percentual de imagens por tema na categoria informada.
* **`POST /api/simulado/materia`**: Gera PDF de simulado focado em uma única matéria.
* **`POST /api/simulado/completo`**: Gera PDF de simulado geral ponderado abrangendo o edital.
* **`POST /api/simulado/cargo/{orgao}/{cargo}`**: Gera PDF de simulado completo ponderado pelos pesos do edital do cargo.
* **`GET /api/simulados/download/{nome}`**: Download direto de arquivos PDF gerados.
* **`POST /api/simulados/zerar`**: Reseta a marcação de questões usadas em simulados.

---

## ⚙️ Guia de Instalação e Execução

### 1. Pré-requisitos
* Python 3.10 ou superior (testado com Python 3.14)
* PostgreSQL 14+ instalado e rodando
* Google Chrome ou Chromium instalado (para automação com Playwright)

### 2. Configurar o Ambiente Virtual

```bash
# Clonar o repositório
git clone git@github.com:Zackzinzz07/banco-de-questoes.git
cd banco-de-questoes

# Criar e ativar o ambiente virtual (.venv)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Instalar os navegadores do Playwright
playwright install chromium
```

### 3. Configurar Conexão com o PostgreSQL

Crie ou edite o arquivo `.env` no diretório raiz do projeto:
```ini
DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco_questoes
TEST_DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco_questoes_test
```

### 4. Executar os Coletores (Scrapers)

```bash
# Coletar enunciados do QConcursos (requer Chrome com perfil logado)
python coletar_qc.py

# Responder questões pendentes e capturar gabaritos no QConcursos (respeita cotas)
python coletar_qc.py gabaritos

# Coletar questões do PCI Concursos (HTML multi-categoria com imagens)
python -m scrapers.pci.coletor_v2

# Arquivar cadernos e gabaritos da Cebraspe em PDF
python coletar_cebraspe.py

# Coletar um concurso específico da Cebraspe
python coletar_cebraspe.py PRF_21
```

### 5. Status e Mapeamento

```bash
# Ver panorama em tempo real do banco de questões
python -m scripts.status

# Detalhar por matéria
python -m scripts.status --materia

# Executar a varredura autônoma de IDs no QConcursos
python scripts/mapear_disciplinas_qc.py
```

---

## 🧪 Testes Automatizados e Qualidade

O projeto mantém uma extensa suíte de testes com mais de **300 testes automatizados** via **`pytest`**, cobrindo parser, banco de dados, sanitização, taxonomia, motores de simulados e rotas da API.

### Executar a Suíte de Testes:

```bash
# Rodar todos os testes unitários e de integração
pytest

# Rodar com relatório de cobertura de código
pytest --cov=. --cov-report=term-missing

# Rodar apenas testes da Web API
pytest tests/test_web_api.py -v
```

### Formatação e Linting:

Seguimos regras estritas configuradas no `ruff.toml` e limites de arquivo descritos em `CLAUDE.md`:
```bash
ruff check .
```

---

<p align="center">
  Desenvolvido com foco em <b>Desempenho</b>, <b>Rigor Editorial</b> e <b>Aprovação em Concursos Públicos</b>.
</p>
