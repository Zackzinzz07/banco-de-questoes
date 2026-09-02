# Diretrizes de Desenvolvimento — Banco de Questões

## 1. Arquitetura e Separação de Responsabilidades
- Limite estrito: nenhum arquivo deve ultrapassar 150 linhas.
- Divisão obrigatória de camadas:
  - `core/scraper.py`: Apenas automação com Playwright (navegação, cliques, waits e obtenção de HTML). Proibido usar BeautifulSoup aqui. Proibido chamar banco de dados.
  - `core/parser.py`: Apenas extração e tratamento com BeautifulSoup (recebe string HTML e devolve modelos tipados). Funções 100% puras, sem I/O de rede ou banco.
  - `core/models.py`: Dataclasses ou Pydantic representando a Questão (enunciado, alternativas, gabarito, banca, ano, etc.).
  - `storage/database.py`: Funções de persistência e queries. Proibido conter lógica de parsing de HTML ou seletores de DOM.
  - `main.py`: Orquestrador linear e limpo (menos de 60 linhas). Apenas coordena as etapas.

## 2. Gestão Crítica de Conexões e Ciclo de Vida
- Injeção de Dependência Obrigatória:
  - Funções no `scraper.py` DEVEM receber a instância de `page: Page` já aberta. Proibido instanciar `sync_playwright()` ou `async_playwright()` dentro de loops ou funções auxiliares.
  - Funções no `database.py` DEVEM receber a conexão/sessão ativa (`conn` ou `session`). Proibido abrir novas conexões de banco por questão processada.
- Fechamento Seguro:
  - Navegador Playwright e conexão com o banco são abertos e fechados EXCLUSIVAMENTE no `main.py`, sempre envelopados em `with` context managers ou blocos `try...finally`.

## 3. Padrões de Código
- Tipagem estrita em todas as assinaturas (`def extrair_html(page: Page, url: str) -> str:`).
- Não gere código preguiçoso com `# TODO` ou reticências `...` em blocos críticos de scraping e persistência.
- Se uma função precisar lidar com layout quebrado ou erro de seletor, trate exceções locais no `parser.py` retornando campos nulos/defaults em vez de quebrar a execução da automação inteira.

## 4. Comandos Rápidos (Skills)
- `/fatiar [arquivo]`: Analise o arquivo e entregue um plano numerado de refatoração em etapas isoladas, sem gerar o código completo de uma vez.
- `/isolar-parser`: Extraia os seletores BeautifulSoup e limpeza de strings para funções puras no `parser.py`.
- `/revisar-recursos`: Verifique se há vazamento de memória, contextos de browser não fechados ou queries abrindo conexões desnecessárias.