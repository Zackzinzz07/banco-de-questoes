# Diretrizes de Desenvolvimento — Banco de Questões

## 1. Arquitetura e Separação de Responsabilidades

### 1.1 Limites de tamanho (verificados por hook, não por boa vontade)
- `scrapers/**` e `simulados/estilos/**`: máximo **250 linhas** por arquivo.
- Demais módulos de aplicação (`web_api.py`, `db.py`, `simulados/**`, raiz): máximo **350 linhas**.
- `tests/**`: **isento**. Cobertura não é dívida técnica e não deve ser desincentivada.
- Orquestradores de CLI (`main.py`, `simulados/cli_multibanca.py`): abaixo de **60 linhas**.
- Dívida conhecida: 27 arquivos hoje excedem esses limites. O hook trava apenas o que for
  editado daqui em diante — não é para refatorar tudo de uma vez.

### 1.2 Divisão obrigatória de camadas
- **Automação** — `scraper_qc.py`, `scrapers/qconcursos_*.py`, `scrapers/prf_federal_scraper.py`,
  `scrapers/pci/coletor*.py`: apenas Playwright (navegação, cliques, waits, obtenção de HTML).
  Proibido BeautifulSoup. Proibido acessar banco de dados.
- **Parsing** — `scrapers/pci/parser.py` e qualquer `**/parser.py`: apenas extração e tratamento
  com BeautifulSoup (recebe string HTML, devolve modelos tipados). Funções 100% puras, sem I/O
  de rede ou banco.
- **Modelos** — dataclasses ou Pydantic representando a Questão (enunciado, alternativas,
  gabarito, banca, órgão, ano).
- **Persistência** — `db.py`, `scripts/importar_sqlite.py`, `migrations/**`: funções de
  persistência e queries. Proibido conter parsing de HTML ou seletores de DOM.
- **Orquestração** — `main.py` e CLIs: linear e limpo, apenas coordena as etapas.

## 2. Gestão Crítica de Conexões e Ciclo de Vida
- Injeção de Dependência Obrigatória:
  - Funções da camada de automação DEVEM receber a instância de `page: Page` já aberta.
    Proibido instanciar `sync_playwright()` ou `async_playwright()` dentro de loops ou funções auxiliares.
  - Funções da camada de persistência DEVEM receber a conexão/sessão ativa (`conn` ou `session`).
    Proibido abrir novas conexões de banco por questão processada.
- Fechamento Seguro:
  - Navegador Playwright e conexão com o banco são abertos e fechados EXCLUSIVAMENTE no
    orquestrador, sempre envelopados em `with` context managers ou blocos `try...finally`.

## 3. Padrões de Código
- Tipagem estrita em todas as assinaturas (`def extrair_html(page: Page, url: str) -> str:`).
- Formatação e lint são aplicados automaticamente por hook via `ruff` (`.venv/bin/ruff`).
- Não gere código preguiçoso com `# TODO` ou reticências `...` em blocos críticos de scraping e persistência.
- Se uma função precisar lidar com layout quebrado ou erro de seletor, trate exceções locais na
  camada de parsing retornando campos nulos/defaults em vez de quebrar a automação inteira.

## 4. Comandos Rápidos (Skills)
- `/fatiar [arquivo]`: Analise o arquivo e entregue um plano numerado de refatoração em etapas isoladas, sem gerar o código completo de uma vez.
- `/isolar-parser`: Extraia os seletores BeautifulSoup e limpeza de strings para funções puras na camada de parsing.
- `/revisar-recursos`: Verifique se há vazamento de memória, contextos de browser não fechados ou queries abrindo conexões desnecessárias.
