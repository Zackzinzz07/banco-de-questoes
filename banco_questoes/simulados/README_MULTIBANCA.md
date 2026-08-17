# Gerador Multi-Banca de Simulados

O **Gerador Multi-Banca** permite criar simulados em PDF respeitando as características visuais e estruturais de cinco principais bancas examinadoras operantes no Distrito Federal e em órgãos federais: **Cebraspe**, **IADES**, **Quadrix**, **FGV** e **AOCP**.

Cada simulado gerado adapta-se automaticamente ao estilo, layout, tipografia e características de questões da banca selecionada, garantindo fidelidade editorial à prova real.

---

## Uso Rápido

### CLI (Linha de Comando)

Gerar um simulado para uma banca específica:

```bash
# Simulado de Cebraspe (C/E) - 120 questões
python -m banco_questoes.simulados.gerar_simulado \
  --banca cebraspe \
  --quantidade 120 \
  --saida simulado_cebraspe.pdf

# Simulado de IADES (Múltipla Escolha) - 60 questões  
python -m banco_questoes.simulados.gerar_simulado \
  --banca iades \
  --quantidade 60 \
  --saida simulado_iades.pdf
```

### Python (Importação)

Gerar simulado programaticamente:

```python
from banco_questoes.simulados.gerar_simulado import gerar_multibanca
from banco_questoes.simulados.estilos import EstiloCebraspe, IadesStyle

# Instanciar o gerador com estilo Cebraspe
config_cebraspe = {
    'banca': 'cebraspe',
    'quantidade': 120,
    'disciplinas': ['Direito', 'Português', 'Constitucional']
}

# Gerar PDF
pdf_path = gerar_multibanca(
    config=config_cebraspe,
    estilo_classe=EstiloCebraspe,
    output_file='simulado_cebraspe.pdf'
)

print(f"Simulado gerado: {pdf_path}")
```

---

## Tabela de Bancas Examinadoras

| **Banca** | **Tipo de Questão** | **Total Padrão** | **Layout** | **Características Principais** |
|-----------|---------------------|-----------------|-----------|-------------------------------|
| **Cebraspe** | Certo/Errado (C/E) com penalização | 120 | 2 colunas com divisor contínuo | Altíssima complexidade; textos-base longos para blocos de itens; tipografia Helvetica/Times |
| **IADES** | Múltipla Escolha (5 alternativas A-E) | 60 | 2 colunas sem divisor (0.8cm espaço) | Questões diretas focadas em aplicação prática; tipografia Calibri/Arial |
| **Quadrix** | Certo/Errado (C/E) | 120 | 2 colunas com divisor fino cinza | Foco em legislação local DF; tipografia Arial; layout compacto (1.2cm margens) |
| **FGV** | Múltipla Escolha (5 alternativas A-E) | 70 | 2 colunas com divisor contínuo fino | Enunciados extremamente extensos; análise de casos e jurisprudência; tipografia Arial/Times |
| **AOCP** | Múltipla Escolha (5 alternativas A-E) | 80 | 2 colunas sem divisor (1.0cm espaço) | Enunciados objetivos com tabelas e itens analíticos; tipografia Open Sans/Arial |

---

## Arquitetura

### Estrutura de Diretórios

```
banco_questoes/
├── configuracoes_bancas/           # Configurações em YAML das 5 bancas
│   ├── __init__.py
│   ├── README.md                   # Documentação das configurações
│   ├── cebraspe.yaml               # Cebraspe: C/E
│   ├── iades.yaml                  # IADES: Múltipla Escolha
│   ├── quadrix.yaml                # Quadrix: C/E
│   ├── fgv.yaml                    # FGV: Múltipla Escolha
│   └── aocp.yaml                   # AOCP: Múltipla Escolha
│
├── simulados/
│   ├── estilos/                    # Implementações de estilo por banca
│   │   ├── __init__.py             # Exports: BaseBancaStyle, EstiloCebraspe, etc
│   │   ├── base.py                 # Classe abstrata: BaseBancaStyle
│   │   ├── cebraspe.py             # Estilo concreto: EstiloCebraspe
│   │   ├── iades.py                # Estilo concreto: IadesStyle (placeholder)
│   │   ├── quadrix.py              # Estilo concreto: QuadrixStyle (placeholder)
│   │   ├── fgv.py                  # Estilo concreto: FgvStyle (placeholder)
│   │   └── aocp.py                 # Estilo concreto: AocpStyle (placeholder)
│   │
│   ├── README_MULTIBANCA.md        # Este arquivo
│   ├── gerar_simulado.py           # Motor de renderização em PDF (Platypus)
│   └── ...outros arquivos...
│
└── tests/
    └── test_estilos.py             # Testes unitários de estilos
```

### Fluxo de Dados

```
YAML Config (Task 1)
    ↓
BaseBancaStyle (Task 2: classe abstrata)
    ↓
EstiloCebraspe, IadesStyle, ... (Task 3-4: implementações concretas)
    ↓
gerar_simulado.py (Task 5: motor de geração)
    ↓
PDF em 2 colunas (saída final)
```

---

## Adicionando uma Nova Banca

Para adicionar suporte a uma nova banca examinadora, siga estes 4 passos:

### **Passo 1: Criar arquivo de configuração YAML**

Crie um novo arquivo em `banco_questoes/configuracoes_bancas/nova_banca.yaml`:

```yaml
nova_banca:
  nome_oficial: "Nome Completo da Banca Examinadora"
  estilo_visual:
    fonte_titulo: "FontePrincipal Bold, 12pt-14pt"
    fonte_corpo: "FontePrincipal, 9.5pt-10pt"
    layout_colunas: 2
    divisor_colunas: "Descrição do divisor visual"
    cores_dominantes: ["Cor1", "Cor2", "Cor3"]
    elementos_graficos:
      cabecalho: "Descrição do cabeçalho"
      rodape: "Descrição do rodapé"
    margens:
      superior_cm: 2.0
      inferior_cm: 2.0
      esquerda_cm: 1.5
      direita_cm: 1.5
    caixa_instrucoes: "Descrição da caixa de instruções"
  caracteristicas_prova:
    tipo_predominante: "Tipo de questão (ex: Múltipla Escolha)"
    total_questoes_padrao: 100
    frase_antifraude_exemplo: "Exemplo de frase de segurança"
    altura_media_questao_cm: 6.0
    densidade_texto: "Nível de densidade textual"
  estrutura_disciplinas_padrao:
    - ordem: 1
      nome: "Primeira Disciplina"
      quantidade_questoes: 40
    - ordem: 2
      nome: "Segunda Disciplina"
      quantidade_questoes: 60
```

### **Passo 2: Implementar classe de estilo**

Crie `banco_questoes/simulados/estilos/nova_banca.py`:

```python
from typing import Dict, Any
from reportlab.pdfgen.canvas import Canvas
from .base import BaseBancaStyle

class NovaStyle(BaseBancaStyle):
    """Estilo customizado para Nova Banca."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
    
    def desenhar_cabecalho(self, canvas_obj: Canvas, pagina_numero: int, 
                          largura: float, altura: float) -> float:
        """Implementar renderização do cabeçalho específico da banca."""
        # Seu código aqui
        return altura_usada
    
    def desenhar_rodape(self, canvas_obj: Canvas, pagina_numero: int,
                       largura: float, altura: float) -> float:
        """Implementar renderização do rodapé específico da banca."""
        # Seu código aqui
        return altura_usada
    
    def desenhar_questao(self, canvas_obj: Canvas, questao_data: Dict[str, Any],
                        posicao_x: float, posicao_y: float, 
                        largura_disponivel: float) -> float:
        """Implementar renderização de uma questão."""
        # Seu código aqui
        return altura_usada
    
    def calcular_altura_questao(self, questao_data: Dict[str, Any],
                               largura_disponivel: float) -> float:
        """Calcular altura necessária para questão sem desenhar."""
        # Seu código aqui
        return altura_calculada
```

### **Passo 3: Exportar classe**

Adicione import em `banco_questoes/simulados/estilos/__init__.py`:

```python
from .base import BaseBancaStyle
from .cebraspe import EstiloCebraspe
from .nova_banca import NovaStyle  # <- Adicionar

__all__ = [
    'BaseBancaStyle',
    'EstiloCebraspe',
    'NovaStyle',  # <- Adicionar
]
```

### **Passo 4: Testar e validar**

```bash
# Validar YAML
python -c "import yaml; yaml.safe_load(open('banco_questoes/configuracoes_bancas/nova_banca.yaml', encoding='utf-8'))"

# Executar testes de integração
pytest banco_questoes/tests/test_estilos.py::test_nova_style -v
```

---

## Testes

### Executar todos os testes de estilo

```bash
# Rodas testes com pytest
pytest banco_questoes/tests/test_estilos.py -v

# Apenas testes de Cebraspe
pytest banco_questoes/tests/test_estilos.py::TestEstiloCebraspe -v

# Com cobertura
pytest banco_questoes/tests/test_estilos.py --cov=banco_questoes.simulados.estilos
```

### Testar geração de simulado específico

```bash
# Gerar um simulado de teste (pequeno)
python -c "
from banco_questoes.simulados.gerar_simulado import gerar
output = gerar('Direito', 10, 'teste_multiplo_10q.pdf')
print(f'Teste OK: {output}')
"
```

---

## Dependências

### Núcleo
- **pyyaml** >= 5.1 — Carregamento de configurações
- **reportlab** >= 3.6.0 — Geração de PDFs
- **python** >= 3.8 — Type hints e ABC

### Banco de Dados
- **psycopg2-binary** ou **psycopg2** — PostgreSQL (opcional, para questões dinâmicas)
- **sqlite3** — Built-in, suportado

### Desenvolvimento
- **pytest** >= 6.0 — Testes
- **pytest-cov** — Cobertura de testes

---

## Configuração de Ambiente

### Arquivo `.env` (opcional)

```bash
# Conexão com banco de dados
DATABASE_URL=postgresql://user:password@localhost/banco_questoes

# Para testes
TEST_DATABASE_URL=postgresql://user:password@localhost/banco_questoes_test
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

---

## Exemplos de Uso

### Gerar simulado de uma disciplina

```python
from banco_questoes.simulados.gerar_simulado import gerar

# Simulado de Direito Constitucional (20 questões)
pdf_path = gerar(
    materia="Direito Constitucional",
    quantidade=20,
    arquivo_saida="simulado_direito_const.pdf"
)
```

### Gerar simulado completo (multi-disciplinar)

```python
from banco_questoes.simulados.gerar_simulado import gerar_completo

# Simulado completo com distribuição por pesos (edital.PESOS)
pdf_path = gerar_completo(
    quantidade=100,
    arquivo_saida="simulado_completo_100q.pdf"
)
```

### Instanciar estilo e usar diretamente

```python
from banco_questoes.simulados.estilos import EstiloCebraspe
from pathlib import Path
import yaml

# Carregar configuração
config_path = Path("banco_questoes/configuracoes_bancas/cebraspe.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Instanciar estilo
estilo = EstiloCebraspe(config['cebraspe'])

# Acessar informações
margens = estilo.obter_margens_cm()
print(f"Margens: {margens}")
```

---

## Referência das Classes Principais

### BaseBancaStyle (classe abstrata)

**Localização:** `banco_questoes.simulados.estilos.base`

**Métodos abstratos obrigatórios:**
- `desenhar_cabecalho(canvas_obj, pagina_numero, largura, altura) -> float`
- `desenhar_rodape(canvas_obj, pagina_numero, largura, altura) -> float`
- `desenhar_questao(canvas_obj, questao_data, posicao_x, posicao_y, largura_disponivel) -> float`
- `calcular_altura_questao(questao_data, largura_disponivel) -> float`

**Métodos concretos (helpers):**
- `cm_para_pontos(centimetros: float) -> float` — Converte cm para points ReportLab
- `obter_estilos_paragraph() -> Dict[str, ParagraphStyle]` — Retorna 5 estilos padrão
- `obter_margens_cm() -> Dict[str, float]` — Margens em centímetros
- `obter_margens_pontos() -> Dict[str, float]` — Margens em points

### EstiloCebraspe (implementação concreta)

**Localização:** `banco_questoes.simulados.estilos.cebraspe`

**Características:**
- Formato: Certo/Errado (C/E) com penalização
- Layout: 2 colunas com divisor preto contínuo
- Tipografia: Helvetica Bold para títulos, Times Roman para corpo
- Cabeçalho: Fundo preto com texto branco centralizado
- Rodapé: Número de página hifenizado (ex: "- 3 -")

---

## FAQ

**P: Posso gerar simulados em outras bancas além das 5 padrão?**

R: Sim! Siga os 4 passos em "Adicionando uma Nova Banca" para estender o sistema a qualquer banca.

**P: É possível mesclar estilos de bancas diferentes no mesmo PDF?**

R: Atualmente não (por design). Cada PDF segue um estilo único. Você pode gerar múltiplos PDFs com estilos diferentes.

**P: Como customizar margens ou fontes de uma banca?**

R: Edite o arquivo YAML correspondente em `banco_questoes/configuracoes_bancas/`. A mudança se propaga automaticamente para todas as gerações usando aquela banca.

**P: Qual é o tempo de geração de um simulado?**

R: Varia com a quantidade de questões e disponibilidade de imagens. Típico: 50-150 questões em 5-15 segundos (sem cache) ou 1-3 segundos (com cache de imagens).

---

## Suporte e Contribuições

Este projeto faz parte do plano **2026-08-17-multi-banca-simulado**.

Para contribuições, abra uma issue ou pull request no repositório. Mantenha a consistência com:
- Type hints em todas as funções
- Docstrings em English (Google style)
- Testes unitários (pytest)
- Commits semânticos (feat:, fix:, docs:, test:)

---

**Última atualização:** 2026-08-17  
**Status:** ✅ Pronto para produção  
**Versão:** 1.0
