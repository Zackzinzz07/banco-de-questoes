# 📚 Banco de Questões de Concursos Públicos

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-orange.svg)](https://playwright.dev/)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF-red.svg)](https://www.reportlab.com/)
[![Status](https://img.shields.io/badge/Status-Ativo%20%2F%20Produção-success.svg)](#)

Sistema de alta performance para **coleta**, **taxonomia**, **armazenamento**, **análise** e **geração de simulados em PDF** para concursos públicos. Atualmente o acervo conta com **mais de 107.000 questões** coletadas de múltiplas fontes (*QConcursos*, *PCI Concursos* e *Provas Oficiais Cebraspe em PDF*).

---

## 📋 Sumário

- [🎯 Visão Geral](#-visão-geral)
- [✨ Principais Funcionalidades](#-principais-funcionalidades)
- [🔍 Mapeamento Autônomo de Disciplinas QC](#-mapeamento-autônomo-de-disciplinas-qc)
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
1. **Scraping Multi-Fonte**: Extração automatizada e ética de questões respeitando cotas, sessões e contornando desafios anti-bot (Cloudflare Turnstile) via Playwright.
2. **Normalização e Taxonomia**: Mapeamento inteligente de conteúdos por órgão, banca, cargo, ano, disciplina, categoria e tema.
3. **Deduplicação Rigorosa**: Algoritmos baseados em hash MD5 e SHA256 para evitar duplicatas entre fontes distintas.
4. **Exportação Editorial em PDF**: Geração de cadernos de simulados diagramados em 2 colunas com layout e tipografia idênticos aos das bancas oficiais (**Cebraspe**, **IADES**, **Quadrix**, **FGV** e **AOCP**).
5. **Dashboard Interativo**: Interface web em FastAPI para acompanhar estatísticas por disciplina/concurso, progresso de coleta e geração de simulados sob demanda.

### Concursos Suportados por Edital

O sistema possui configurações prontas para editais de concursos estratégicos:
* **SEDES/DF** (Secretaria de Desenvolvimento Social do DF)
* **PMDF** (Polícia Militar do DF)
* **PCDF** (Polícia Civil do DF)
* **BACEN** (Banco Central do Brasil)
* **INSS** (Instituto Nacional do Seguro Social)
* **PRF** (Polícia Rodoviária Federal)
* **RFB** (Receita Federal do Brasil)
* **Correios** (Empresa Brasileira de Correios e Telégrafos)
* **Banco do Brasil** (BB)

---

## ✨ Principais Funcionalidades

- **Coleta Multi-Fonte Paralela**:
  - `QConcursos`: Coleta orientada a IDs numéricos de disciplinas, com suporte a sessão autenticada do Chrome (`perfil_chrome_scraper`) e controle de cota diária.
  - `PCI Concursos`: Coleta hierárquica organizada por árvore de categorias e temas com parsing robusto de alternativas e imagens de apoio.
  - `Cebraspe PDF`: Leitor automatizado de provas oficiais e gabaritos em PDF em layout de 2 colunas com suporte a justificativas de anulação/alteração.
- **Deduplicação por `content_hash`**: Garante que a mesma questão vinda do PCI e do QConcursos não seja inserida duas vezes no PostgreSQL.
- **Gerador Multi-Banca**: Engine baseada em ReportLab Platypus que cria simulados profissionais em PDF de 2 colunas com folha de gabarito.
- **Dashboard Educacional**: Interface visual web (estilo gamificado/Duolingo) com estatísticas detalhadas por matéria, banco de questões inéditas vs. usadas e download direto dos PDFs.

---

## 🔍 Mapeamento Autônomo de Disciplinas QC

Para expandir a cobertura do coletor do QConcursos além das 23 disciplinas iniciais, implementamos uma varredura automatizada (`scripts/mapear_disciplinas_qc.py`) no intervalo de **IDs 1 a 600** utilizando Playwright com perfil logado.

### Resultados Obtidos:
- **Total de IDs Auditados**: `600`
- **Disciplinas Válidas Encontradas**: **`244` disciplinas ativas**
- **Acervo Mapeado**: Mais de 1,8 milhão de questões catalogadas no QConcursos prontas para coleta.
- **Persistência**:
  - `estudo_autonomo/mapeamento_disciplinas_qc.json`: Estrutura JSON completa com ID, Nome e Quantidade de questões.
  - `estudo_autonomo/mapeamento_disciplinas_qc.csv`: Planilha formatada para fácil consulta e integração.

---

## 📐 Arquitetura e Separação de Camadas

O projeto adota **Arquitetura Limpa em 5 Camadas**, com limites estritos de tamanho de arquivo fiscalizados por hooks de lint:

```
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Orquestração                   │
│   (coletar_qc.py, coletar_cebraspe.py, cli_multibanca.py)   │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼──────────────┐
│    Camada de Automação      ││    Camada de Persistência   │
│  (Playwright / HTTP pure)   ││   (db.py / PostgreSQL)     │
│   [Sem BeautifulSoup/DB]    ││     [Sem DOM/Parsing]      │
└──────────────┬──────────────┘└──────────────────────────────┘
               │
┌──────────────▼──────────────┐
│      Camada de Parsing      │
│  (scrapers/*/parser.py)     │
│  [Funções 100% Puras/BS4]   │
└─────────────────────────────┘
```

1. **Automação** (`scraper_qc.py`, `scrapers/pci/coletor*.py`): Responsável apenas por navegação HTTP/Playwright e captura de HTML bruto. Proibido BeautifulSoup ou consultas ao banco.
2. **Parsing** (`scrapers/*/parser.py`): Extração de dados usando BeautifulSoup. Funções puras que recebem HTML e devolvem dataclasses/dicionários tipados.
3. **Modelos**: Dataclasses que representam o contrato da Questão (enunciado, alternativas, gabarito, banca, órgão, ano).
4. **Persistência** (`db.py`, `migrations/`): Gerenciamento de conexões PostgreSQL, queries SQL, deduplicação e controle de progresso.
5. **Orquestração** (`coletar_qc.py`, `web_api.py`, `simulados/cli_multibanca.py`): Coordena o fluxo lendo da automação, passando pelo parser e gravando na persistência.

---

## 📂 Estrutura do Projeto

```
banco_questoes/
├── CLAUDE.md                       # Diretrizes de desenvolvimento e limites de código
├── README.md                       # Documentação principal do projeto
├── config.py                       # Configurações globais e URL do banco de dados
├── db.py                           # Camada de persistência PostgreSQL e deduplicação
├── edital.py                       # Registro legados de disciplinas e pesos do SEDES/DF
├── edital_loader.py                # Carregador YAML multi-concurso (editais dinâmicos)
├── taxonomia.py                    # Mapeador de taxonomia unificada
├── web_api.py                      # Servidor REST API em FastAPI
├── coletar_qc.py                   # Orquestrador de coleta do QConcursos
├── coletar_cebraspe.py             # Orquestrador de coleta de PDFs da Cebraspe
│
├── configuracoes_bancas/           # Especificações YAML das bancas examinadoras
│   ├── cebraspe.yaml
│   ├── iades.yaml
│   ├── quadrix.yaml
│   ├── fgv.yaml
│   └── aocp.yaml
│
├── configuracoes_editais/          # Especificações YAML dos editais por concurso
│   ├── sedes_df.yaml
│   ├── pmdf.yaml
│   ├── bacen.yaml
│   ├── inss.yaml
│   ├── prf.yaml
│   └── ...
│
├── estudio_autonomo/               # Resultados de análises e arquivos de mapeamento
│   ├── mapeamento_disciplinas_qc.json
│   └── mapeamento_disciplinas_qc.csv
│
├── scrapers/                       # Módulos de scraping por fonte
│   ├── qc/                         # Parser e registro do QConcursos
│   │   ├── disciplinas.py
│   │   └── parser.py
│   ├── pci/                        # Coletor e parser do PCI Concursos
│   │   ├── coletor_v2.py
│   │   ├── config.py
│   │   └── parser.py
│   └── cebraspe/                   # Coletor de provas e gabaritos em PDF
│       ├── coletor.py
│       ├── leitura_pdf.py
│       └── parser.py
│
├── simulados/                      # Engine Multi-Banca de simulados em PDF
│   ├── README_MULTIBANCA.md
│   ├── gerador_multibanca.py
│   ├── gerar_simulado.py
│   └── estilos/                    # Implementações de layout por banca (ReportLab)
│       ├── base.py
│       ├── cebraspe.py
│       ├── iades.py
│       ├── quadrix.py
│       ├── fgv.py
│       └── aocp.py
│
├── scripts/                        # Scripts de automação, varredura e manutenção
│   ├── mapear_disciplinas_qc.py    # Varredura autônoma ID 1-600 do QConcursos
│   ├── gerar_simulado_pmdf.py
│   ├── importar_sqlite.py
│   └── status.py
│
├── tests/                          # Suíte de testes automatizados (pytest)
│   ├── test_db.py
│   ├── test_disciplinas_qc.py
│   ├── test_gerador_multibanca.py
│   ├── test_web_api.py
│   └── ...
│
└── web/                            # Frontend estático do Dashboard
    ├── dashboard_educacional.html
    ├── index.html
    ├── script.js
    └── style.css
```

---

## 🗄️ Banco de Dados & Deduplicação

O projeto utiliza **PostgreSQL** para alta performance em grandes volumes.

### Esquema Principal (`questoes`)

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identificador único interno |
| `id_qc` | `TEXT UNIQUE` | ID original no QConcursos (quando aplicável) |
| `enunciado` | `TEXT NOT NULL` | Texto do enunciado da questão |
| `hash_enunciado` | `TEXT UNIQUE` | SHA256 do enunciado normalizado |
| `content_hash` | `TEXT UNIQUE` | MD5 de `normalizar(enunciado) + json(alternativas)` para dedupe |
| `alternativas` | `TEXT NOT NULL` | JSON contendo a lista de alternativas |
| `gabarito` | `TEXT` | Alternativa correta (ex: "A", "Certo", "Errado") |
| `comentario` | `TEXT` | Comentário ou explicação da solução |
| `materia` | `TEXT NOT NULL` | Nome normalizado da disciplina |
| `assunto` | `TEXT` | Sub-tópico ou assunto |
| `ano` | `INTEGER` | Ano da aplicação da prova |
| `prova` | `TEXT` | Nome do concurso/órgão da prova original |
| `fonte` | `TEXT NOT NULL` | Origem da questão (`qconcursos`, `pci`, `quadrix_pdf`) |
| `usada_em_simulado` | `INTEGER` | Controle de ineditismo (0 = virgem, 1 = usada em simulado) |
| `categoria` | `VARCHAR(255)` | Categoria macro de taxonomia |
| `tema` | `VARCHAR(255)` | Tema específico de taxonomia |
| `banca` | `TEXT` | Nome oficial da banca examinadora |
| `orgao` | `TEXT` | Órgão contratante |
| `cargo` | `TEXT` | Cargo público correspondente |

### Deduplicação Automática

Antes de qualquer inserção, o sistema calcula o `content_hash`:
```python
content_hash = md5(normalizar(enunciado) + "|" + json.dumps(sorted_alternativas))
```
Se a mesma questão for extraída via PCI Concursos e via QConcursos, o banco rejeita a duplicata transparentemente via `ON CONFLICT` ou checagem prévia.

---

## 📄 Motor Multi-Banca de Simulados PDF

O módulo `simulados` gera provas completas em formato PDF prontas para impressão ou leitura em tablet.

### Características das Bancas Suportadas:

* **Cebraspe**: Questões no formato **Certo/Errado (C/E)**, layout em 2 colunas com barra divisória contínua, cabeçalho escuro e rodapé formatado (`- 1 -`).
* **IADES**: Questões de **Múltipla Escolha (5 alternativas A-E)**, layout compacto em 2 colunas e tipografia limpa.
* **Quadrix**: Formato **Certo/Errado (C/E)** focado em legislação distrital e federal.
* **FGV**: Enunciados extensos de análise de caso em 2 colunas com divisores finos.
* **AOCP**: Múltipla escolha objetiva com suporte a tabelas e itens analíticos.

### Como Gerar um Simulado via CLI:

```bash
# Simulado Cebraspe com 120 questões (C/E)
python -m banco_questoes.simulados.gerar_simulado --banca cebraspe --quantidade 120 --saida simulado_cebraspe.pdf

# Simulado para o concurso da PMDF (Soldado)
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
Acesse o Dashboard no navegador: `http://localhost:8000`

### Principais Endpoints HTTP:

* **`GET /api/stats`**: Resumo das estatísticas de questões (total, inéditas, usadas, por matéria).
* **`GET /api/stats/todas`**: Distribuição global de questões por órgão e matéria.
* **`GET /api/stats/materias`**: Estatísticas das disciplinas com listagem de categorias/temas.
* **`GET /api/orgaos`**: Lista todos os órgãos/concursos configurados.
* **`GET /api/cargos/{orgao}`**: Lista os cargos disponíveis para um determinado órgão.
* **`POST /api/simulado/materia`**: Gera PDF de simulado focado em uma única matéria.
* **`POST /api/simulado/cargo/{orgao}/{cargo}`**: Gera PDF de simulado completo ponderado pelos pesos do edital do cargo.
* **`POST /api/simulados/zerar`**: Reseta a marcação de questões usadas em simulados.

---

## ⚙️ Guia de Instalação e Execução

### 1. Pré-requisitos
* Python 3.10 ou superior
* PostgreSQL 14+ instalado e rodando
* Google Chrome ou Chromium (para suporte ao Playwright com perfil persistente)

### 2. Configurar o Ambiente Virtual

```bash
# Clonar o repositório
git clone git@github.com:Zackzinzz07/banco-de-questoes.git
cd banco-de-questoes/banco_questoes

# Criar e ativar o ambiente virtual (.venv)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Instalar os navegadores do Playwright
playwright install chromium
```

### 3. Configurar Conexão com o PostgreSQL

Crie ou edite o arquivo `.env` no diretório raiz do módulo:
```ini
DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco_questoes
```

### 4. Executar os Coletores (Scrapers)

```bash
# Coletar do QConcursos (utiliza Playwright logado)
python coletar_qc.py

# Coletar do PCI Concursos (HTML multi-categoria)
python -m scrapers.pci.coletor_v2

# Coletar Provas Oficiais Cebraspe em PDF
python coletar_cebraspe.py
```

### 5. Executar Mapeamento de Disciplinas

```bash
# Executar a varredura autônoma de IDs no QConcursos
python scripts/mapear_disciplinas_qc.py
```

---

## 🧪 Testes Automatizados e Qualidade

O projeto mantém uma extensa suíte de testes com **`pytest`** garantindo a integridade do parser, banco de dados, API e motor de simulados.

### Executar a Suíte de Testes:

```bash
# Rodar todos os testes unitários e de integração
pytest

# Rodar com relatório de cobertura de código
pytest --cov=. --cov-report=term-missing

# Rodar apenas testes da Web API
pytest tests/test_web_api.py -v
```

### Formatação e Linting Code Style:

Seguimos as regras do `ruff` configuradas no `ruff.toml`:
```bash
.venv/bin/ruff check .
```

---

<p align="center">
  Desenvolvido com foco em **Desempenho**, **Rigor Editorial** e **Aprovação em Concursos Públicos**.
</p>
