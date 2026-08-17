# Configurações de Editais - Multi-Concurso

Este diretório contém configurações YAML para diferentes concursos e seus editais.

## Estrutura YAML

Cada arquivo YAML segue a estrutura abaixo (foco em provas objetivas):

```yaml
concurso_key:
  nome: "Official name"
  banca: "Exam board name (Cebraspe, FGV, IBFC, Cesgranrio, Instituto Quadrix)"
  ano: 2021 | 2022 | 2023 | 2024 | 2026
  orgao: "Agency/Institution name"
  formato: "Certo_Errado | Multipla_Escolha"
  total_questoes: 120
  tempo_minutos: 210  # exam duration in minutes
  
  cargos:
    "Cargo Name":
      nivel: "médio | superior"
      vagas: 1500  # (optional)
      materias:
        "Subject Name": questoes_count
        "Another Subject": questoes_count
```

## Concursos Disponíveis

- **sedes_df.yaml**: SEDES/DF TDAS (Quadrix, 60 questões, 8 matérias)
- **prf.yaml**: PRF Policial (Cebraspe, 120 questões, Legislação Trânsito = 30)
- **bacen.yaml**: BACEN Técnico (Cebraspe, 120 questões, 2 áreas)
- **receita_federal.yaml**: RFB (FGV, 140 Auditor / 110 Analista)
- **inss.yaml**: INSS Técnico (Cebraspe, 120 questões, Seguridade Social = 60)
- **correios.yaml**: Correios (IBFC, 50 questões, múltiplos cargos)
- **banco_brasil.yaml**: BB (Cesgranrio, 70 questões, 2 cargos)

## Fallback Behavior

Se um concurso não tiver YAML, o sistema fará fallback para a configuração hardcoded em `edital.py` (apenas SEDES/DF).

## Validação

Para validar a sintaxe YAML:

```bash
python -c "import yaml; yaml.safe_load(open('sedes_df.yaml'))"
```
