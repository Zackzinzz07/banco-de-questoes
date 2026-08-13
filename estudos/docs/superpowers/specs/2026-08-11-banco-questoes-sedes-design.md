# Design — Banco de Questões SEDES/DF (cargo 202 TDAS Técnico Administrativo)

**Data:** 2026-08-11 · **Prova:** 06/09/2026 (tarde) · **Banca:** Instituto Quadrix

## Objetivo

Maximizar o número de questões de estudo alinhadas ao conteúdo programático do
Edital nº 1/2026 (item 20), armazenando tudo num banco SQLite local e gerando
simulados em PDF por matéria no modelo do simulado atual (questões numeradas +
seção de Gabarito Comentado ao final).

## Decisões já tomadas

- **Abordagem A (híbrida):** scraper do QConcursos (conta gratuita do usuário)
  + coletor de provas oficiais em PDF do site da Quadrix. Duas fontes, um banco.
- **Várias bancas, não só Quadrix:** o conteúdo do edital aparece em provas de
  muitas bancas; a busca no QC filtra por disciplina/assunto **sem filtro de
  banca**. O campo `banca` de cada questão registra a origem. A Quadrix segue
  sendo a banca de referência (é a banca da prova) e a única fonte de PDFs.
- **Sem comentários por IA** por enquanto (sem API): questão sem comentário
  mostra só a letra do gabarito; comentário do QC é salvo quando visível.
- **SQLite** (`banco_de_questoes.db`), sem servidor — projeto pessoal, usuário
  iniciante em Python.
- Fontes descartadas por ora: Gran Questões (fica como evolução futura).

## Estrutura

```
banco_questoes/
├── banco_de_questoes.db      # SQLite
├── db.py                     # conexão, criação de tabela, salvar/buscar/dedupe
├── edital.py                 # matérias e assuntos do edital + mapeamento p/ filtros do QC
├── scraper_qc.py             # Playwright (Chrome, perfil dedicado do scraper)
├── coletor_quadrix.py        # requests + BeautifulSoup + pdfplumber
└── simulados/
    ├── gerar_simulado.py     # motor de PDF (ReportLab, modelo do simulado atual)
    ├── questoes_portugues.py # exemplo: chama o motor com (matéria, N)
    └── questoes_<materia>.py # um script curto por matéria
```

Fica separado do projeto Django existente em `estudos/`.

## Banco de dados

Tabela única `questoes`:

| campo | tipo | observação |
|---|---|---|
| `id` | INTEGER PK | autoincremento |
| `id_qc` | TEXT UNIQUE nullable | ex.: Q4619278; vazio p/ questões de PDF |
| `enunciado` | TEXT | |
| `alternativas` | TEXT (JSON) | `{"A": "...", "B": "..."}`; Certo/Errado usa `{"C": "Certo", "E": "Errado"}` |
| `gabarito` | TEXT nullable | letra; null enquanto não coletado |
| `comentario` | TEXT nullable | gabarito comentado quando disponível |
| `materia` | TEXT | uma das 8 matérias do edital (nomes canônicos do `edital.py`) |
| `assunto` | TEXT nullable | vem do QC; vazio nas extraídas de PDF |
| `banca`, `orgao`, `ano`, `prova` | TEXT/INT | metadados de origem |
| `fonte` | TEXT | `qconcursos` ou `quadrix_pdf` |
| `usada_em_simulado` | INTEGER (0/1) | marca anti-repetição; comando p/ zerar |

**Dedupe:** `id_qc` único + hash do enunciado normalizado (minúsculas, sem
espaços extras) como segunda trava — provas da Quadrix também existem no QC.

## Matérias do edital (conteúdo de `edital.py`)

Extraídas do Edital nº 1/2026, itens 20.2.2 e 20.2.3 (cargo 202):

1. **Língua Portuguesa** — interpretação, gêneros, ortografia, coesão,
   morfossintaxe, pontuação, concordância, regência, crase, reescrita.
2. **Conhecimentos do DF e Legislação** — DF/RIDE (LC 94/1998), PDPM, Lei
   Orgânica do DF (Título VI), LC 840/2011 (Títulos I, V, VI, VII), Lei Maria
   da Penha (11.340/2006), Lei Distrital 7.484/2024, primeiros socorros.
3. **SUAS** — PNAS/2004, SUAS (princípios, seguranças), NOB/SUAS 2012.
4. **Programas e Benefícios do DF** — Cartão Prato Cheio (7.009/2021), Cartão
   Gás (6.938/2021), Plano DF Social (7.008/2021), Benefícios Eventuais
   (5.165/2013), SISAN/Restaurante Comunitário (Dec. 33.329/2011).
5. **Direito Constitucional** — princípios fundamentais, direitos e garantias,
   organização do Estado e da Administração, servidores públicos.
6. **Direito Administrativo** — Estado/governo/administração, ato
   administrativo, poderes, LC 840/2011 (provimento, vacância, PAD).
7. **Atendimento, Rotinas Administrativas e Arquivologia** — atendimento ao
   público, redação oficial, protocolo, métodos de arquivamento, digitalização.
8. **Recursos Materiais, Patrimônio e Compras** — estoques, armazenagem,
   patrimônio (tombamento, inventário, baixa), Lei 14.133/2021.

Cada matéria carrega: nome canônico (vai no campo `materia`), lista de assuntos
do edital e o(s) valor(es) de filtro correspondentes no QC (disciplina/assunto).
Não entram: RLM, informática, atualidades gerais (não caem nesta prova).

## Coletor 1 — `scraper_qc.py` (Playwright)

*(Decidido em 11/08/2026: Playwright no lugar de Selenium — o Chrome v151
bloqueou automação sobre o perfil padrão do usuário. O scraper usa um perfil
dedicado `perfil_chrome_scraper/` via `launch_persistent_context` +
`channel="chrome"`: na primeira execução abre janela para o usuário logar no
QC; o login fica salvo no perfil. Headless foi testado e o Cloudflare do QC
bloqueia ("Um momento…"), então a coleta roda com janela visível —
minimizável; o marcador confiável de sessão logada é o link "Sair"/`conta/sair`,
não a ausência de `/conta/entrar`.)*

1. Abre o Chrome com perfil dedicado persistente; nenhuma senha no código.
2. Para cada matéria do `edital.py`, monta a URL de busca
   (`qconcursos.com/questoes-de-concursos/questoes?...`) com filtros:
   disciplina/assuntos, excluir anuladas e desatualizadas.
3. Pagina pela numeração (1, 2, 3 … ▶) alterando o parâmetro de página; espera
   os blocos de questão renderizarem; extrai por bloco: `Qxxxxx`, matéria,
   assunto, ano, banca, órgão, prova, enunciado, alternativas.
4. Salva incremental no banco (dedupe automático). Progresso (última página por
   matéria) fica numa tabela `progresso_scraper` para retomar no dia seguinte.
5. **Gabaritos:** para questões sem gabarito no banco, usa a cota diária da
   conta free clicando em "Responder" e capturando gabarito + comentário
   visível. Ao detectar o aviso de limite atingido, para essa fase sem erro.
6. Ritmo educado: pausas de 3–6 s entre páginas; sessão diária única.

**Risco assumido:** raspar o QC contraria os termos de uso; uso pessoal, conta
própria, ritmo lento. O usuário está ciente.

## Coletor 2 — `coletor_quadrix.py` (requests + BS4 + pdfplumber)

1. Lista concursos encerrados no site da Quadrix e seleciona provas cujos
   cargos tenham matérias em comum com o edital (nível médio, mesmo perfil).
2. Baixa PDF da prova + gabarito definitivo para `banco_questoes/provas_pdf/`
   (cache local; não re-baixa).
3. Parser: identifica seções da prova (títulos de matéria), separa questões por
   número, extrai enunciado + alternativas, casa com o gabarito oficial pelo
   número da questão.
4. Mapeia o título da seção para a matéria canônica via `edital.py`; `assunto`
   fica vazio.
5. Questões ilegíveis para o parser são puladas e listadas num relatório final
   (`relatorio_extracao.txt`) — nunca abortam a prova inteira.

## Geradores de PDF — `simulados/`

- `gerar_simulado.py` expõe `gerar(materia, quantidade, arquivo_saida)`:
  1. Sorteia N questões da matéria com `usada_em_simulado = 0` (se faltar,
     avisa e completa com repetidas).
  2. Gera PDF em ReportLab no modelo visual do simulado atual: capa, questões
     numeradas com alternativas, seção final **Gabarito Comentado** (letra +
     comentário quando houver; só a letra quando não).
  3. Marca as questões usadas.
- `questoes_<materia>.py`: script de ~5 linhas com `MATERIA` e `QUANTIDADE`
  editáveis no topo, chamando o motor. Um por matéria do edital.
- Utilitário para zerar `usada_em_simulado` quando o usuário quiser reciclar.

## Erros e limites

- Sem internet / site fora: mensagem clara e sair; nada de traceback cru.
- Limite diário do QC: parar a fase de gabaritos normalmente e informar quanto
  coletou; enunciados continuam sendo coletados (listagem não consome cota).
- Mudança de layout do QC: seletores centralizados no topo do `scraper_qc.py`
  para ajuste fácil.
- PDF da Quadrix fora do padrão: pular questão, registrar no relatório.

## Testes

- `db.py`: testes de inserção, dedupe (id_qc e hash) e sorteio sem repetição.
- Parser da Quadrix: teste com 1 PDF real baixado (fixture) conferindo
  contagem de questões e casamento com gabarito.
- Scraper QC: função de parsing de bloco testada com HTML salvo de exemplo
  (fixture), sem depender de rede.
- Gerador de PDF: teste de fumaça — gera PDF com 3 questões fake e verifica
  que o arquivo existe e abre.

## Fase 2 (decidida em 11/08/2026 — substitui o antigo "fora de escopo: interface web")

- **Simulado Geral Completo:** PDF único com quantidade escolhida na hora,
  distribuída proporcionalmente entre as 8 matérias por pesos editáveis
  (`edital.PESOS`), numeração contínua, seções por matéria, gabarito ao final.
- **Estatísticas do banco:** total / inéditas / usadas / sem gabarito por matéria.
- **Dashboard web (FastAPI + página estática):** ver estatísticas, disparar a
  coleta do QC, gerar e baixar simulados, zerar histórico.
- **Docker:** `Dockerfile` + `docker-compose.yml` para o dashboard e geração de
  PDFs. **A coleta do QC fica fora do Docker** (precisa de janela do Chrome com
  login do usuário — perfil dedicado `perfil_chrome_scraper/`); no contêiner o
  botão de coleta aparece desabilitado (`COLETA_DISPONIVEL=0`).
- Plano: `estudos/docs/superpowers/plans/2026-08-11-web-simulados-fase2.md`.

## Fora de escopo (por enquanto)

- Comentários gerados por IA.
- Gran Questões e outras plataformas.
- Agendamento automático no Windows (roda manual 1x/dia; agendar é evolução).
