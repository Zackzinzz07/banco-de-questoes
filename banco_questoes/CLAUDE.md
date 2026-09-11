# Diretrizes de Desenvolvimento — Banco de Questões

## 1. Arquitetura e Separação de Responsabilidades

### 1.1 Limites de tamanho (verificados por hook, não por boa vontade)
- `scrapers/**` e `simulados/estilos/**`: máximo **500 linhas** por arquivo.
- Demais módulos de aplicação (`web_api.py`, `db.py`, `simulados/**`, raiz): máximo **850 linhas**.
- `tests/**`: **isento**. Cobertura não é dívida técnica e não deve ser desincentivada.
- Orquestradores de CLI (`main.py`, `simulados/cli_multibanca.py`): abaixo de **150 linhas**.
- Permite crescimento saudável e desacoplamento sem sufocar o desenvolvimento nem exigir micro-fatiamentos prematuros.

### 1.2 Divisão obrigatória de camadas
- **Automação** — `scraper_qc.py` e `scrapers/pci/coletor*.py`: apenas Playwright ou HTTP
  (navegação, cliques, waits, obtenção de HTML). Proibido BeautifulSoup. Proibido acessar
  banco de dados.
- **Parsing** — `scrapers/qc/parser.py`, `scrapers/pci/parser.py` e qualquer `**/parser.py`:
  apenas extração e tratamento com BeautifulSoup (recebe string HTML, devolve modelos
  tipados). Funções 100% puras, sem I/O de rede ou banco.
- **Modelos** — dataclasses ou Pydantic representando a Questão (enunciado, alternativas,
  gabarito, banca, órgão, ano).
- **Persistência** — `db.py`, `scripts/importar_sqlite.py`, `migrations/**`: funções de
  persistência e queries. Proibido conter parsing de HTML ou seletores de DOM.
- **Orquestração** — `coletar_qc.py`, `main.py` e CLIs: linear e limpo, apenas coordena as
  etapas. É a única camada que pode falar com mais de uma das outras: abre navegador e
  conexão, passa o HTML da automação para o parser e o resultado do parser para a
  persistência, e fecha tudo em `try/finally`.

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

## 4. Editais (`configuracoes_editais/*.yaml`)
- Matéria, peso e conteúdo programático de cada cargo vêm SEMPRE do edital
  oficial publicado — nunca de estimativa, "achismo" ou generalização de
  outro concurso parecido. Achado real: o cargo Soldado da PMDF tinha uma
  config inventada (matérias que não existem em edital nenhum, ex.:
  "Legislação Específica da PMDF e RIDE"); trocar pelo Edital nº
  04/2023-DGP/PMDF fez o simulado sair de 120 questões fictícias pra 80
  questões reais, com 10 das 12 matérias batendo direto no acervo.
- Todo cargo tem `fonte_edital` (número e data do edital exatamente como na
  capa) e, quando o peso individual de uma matéria não vem explícito no
  edital (só o total de um grupo, tipo "Conhecimentos Específicos: 40
  questões"), marca cada matéria desse grupo com comentário `# CONFERIR` —
  nunca divide e apresenta como se fosse dado oficial.
- Se o cargo não tem edital publicado ainda (concurso futuro, sem edital de
  abertura), NÃO cria a config projetando/estimando — mesmo princípio do
  guardrail de `taxonomia.resolver`: na dúvida, não inventa. Usa o edital do
  último concurso do mesmo cargo que de fato aconteceu, e documenta isso no
  `fonte_edital`.
- Conteúdo programático completo (os tópicos dentro de cada matéria, não só
  o nome) vai num arquivo `<slug>_<cargo>_conteudo_programatico.yaml` ao
  lado do edital principal — é a fonte de dados para uma futura tabela
  `materias` → `conteudos` no banco, então o texto do tópico é cópia literal
  do edital, nunca resumo ou paráfrase.

## 5. Comandos Rápidos (Skills)
- `/fatiar [arquivo]`: Analise o arquivo e entregue um plano numerado de refatoração em etapas isoladas, sem gerar o código completo de uma vez.
- `/isolar-parser`: Extraia os seletores BeautifulSoup e limpeza de strings para funções puras na camada de parsing.
- `/revisar-recursos`: Verifique se há vazamento de memória, contextos de browser não fechados ou queries abrindo conexões desnecessárias.
