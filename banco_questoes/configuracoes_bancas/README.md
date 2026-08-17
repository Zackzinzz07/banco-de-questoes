# Configurações das Bancas Examinadoras

Este diretório contém especificações estruturadas em YAML para as cinco principais bancas examinadoras operantes no Distrito Federal e órgãos federais com sede em Brasília.

## Bancas Incluídas

### 1. **Cebraspe** (cebraspe.yaml)
- **Nome Oficial**: Centro Brasileiro de Pesquisa em Avaliação e Seleção e de Promoção de Eventos
- **Formato Predominante**: Certo / Errado (C/E) com penalização por erro
- **Tipografia**: Helvetica / Arial Bold (títulos), Times New Roman / Helvetica (corpo)
- **Layout**: 2 colunas com linha divisória contínua
- **Total Padrão de Questões**: 120
- **Margens**: 2.0cm (superior/inferior), 1.5cm (laterais)
- **Características**: Altíssima complexidade; textos-base longos para blocos de itens

### 2. **IADES** (iades.yaml)
- **Nome Oficial**: Instituto Americano de Desenvolvimento
- **Formato Predominante**: Múltipla Escolha (5 alternativas: A, B, C, D, E)
- **Tipografia**: Calibri / Arial Bold (títulos), Calibri / Arial (corpo)
- **Layout**: 2 colunas sem linha divisória (espaçamento medianiz)
- **Total Padrão de Questões**: 60
- **Margens**: 1.5cm (uniformes)
- **Características**: Questões diretas focadas na aplicação prática

### 3. **Instituto Quadrix** (quadrix.yaml)
- **Nome Oficial**: Instituto Quadrix
- **Formato Predominante**: Certo / Errado (C/E) em concursos distritais
- **Tipografia**: Arial Bold (títulos), Arial (corpo)
- **Layout**: 2 colunas com linha divisória fina cinza
- **Total Padrão de Questões**: 120
- **Margens**: 1.2cm (uniformes, mais compactas)
- **Características**: Foco ostensivo na legislação local do DF

### 4. **FGV** (fgv.yaml)
- **Nome Oficial**: Fundação Getulio Vargas (FGV Conhecimento)
- **Formato Predominante**: Múltipla Escolha (5 alternativas: A, B, C, D, E)
- **Tipografia**: Arial / Times New Roman Bold (títulos), Times New Roman / Arial (corpo)
- **Layout**: 2 colunas com linha divisória contínua fina
- **Total Padrão de Questões**: 70
- **Margens**: 2.0cm (superior/inferior), 1.5cm (laterais)
- **Características**: Enunciados extremamente extensos; análise de casos e jurisprudência

### 5. **Instituto AOCP** (aocp.yaml)
- **Nome Oficial**: Instituto AOCP
- **Formato Predominante**: Múltipla Escolha (5 alternativas: A, B, C, D, E)
- **Tipografia**: Open Sans / Arial Bold (títulos), Open Sans / Arial (corpo)
- **Layout**: 2 colunas sem linha divisória (espaçamento de 1.0cm)
- **Total Padrão de Questões**: 80
- **Margens**: 1.5cm (uniformes)
- **Características**: Enunciados objetivos com tabelas e itens analíticos

## Estrutura dos Arquivos YAML

Cada arquivo YAML contém os seguintes campos:

### `estilo_visual`
Especificações de tipografia, layout e elementos gráficos:
- `fonte_titulo`: Família e tamanho da fonte de títulos
- `fonte_corpo`: Família e tamanho da fonte de corpo de texto
- `layout_colunas`: Número de colunas (sempre 2)
- `divisor_colunas`: Descrição do divisor visual entre colunas
- `cores_dominantes`: Paleta de cores da banca
- `elementos_graficos`: Cabeçalho, rodapé e instruções
- `margens`: Margens em centímetros (superior, inferior, esquerda, direita)
- `caixa_instrucoes`: Descrição do bloco de instruções

### `caracteristicas_prova`
Parâmetros de estrutura da prova:
- `tipo_predominante`: Formato das questões (C/E ou Múltipla Escolha)
- `total_questoes_padrao`: Quantidade padrão de questões
- `frase_antifraude_exemplo`: Exemplo de frase de segurança ou identificação
- `altura_media_questao_cm`: Altura média ocupada por cada questão
- `densidade_texto`: Nível de densidade textual

### `estrutura_disciplinas_padrao`
Distribuição padrão de disciplinas e quantidade de questões:
- `ordem`: Sequência da disciplina no caderno
- `nome`: Nome da disciplina ou bloco temático
- `quantidade_questoes`: Número de questões nesta disciplina

## Uso

Os arquivos YAML neste diretório podem ser usados para:
- Geração automática de provas simuladas respeitando o padrão de cada banca
- Validação de estrutura de questões
- Referência para diagramação editorial
- Testes de compatibilidade com formatos de diferentes organizadoras
- Treinamento e simulação de concursos públicos

## Validação

Todos os arquivos YAML foram validados sintaticamente antes da inclusão neste repositório.

## Referências

Os dados contidos nestes arquivos foram extraídos da análise de:
- Editais e provas oficiais publicadas pelas bancas
- Cadernos de prova impressos dos últimos 5 anos
- Diretrizes de acessibilidade e segurança aplicáveis no Distrito Federal

## Autor e Data

- **Plano**: 2026-08-17-multi-banca-simulado
- **Task**: 1 - Create Banca Configuration Files (YAML)
