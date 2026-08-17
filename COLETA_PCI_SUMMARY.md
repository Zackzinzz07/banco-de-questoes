# Coleta PCI - Resumo Executivo

## Status Atual ✅

**Data:** 2026-08-17  
**Questões Coletadas:** 30.226 total
- SEDES/DF: 10.170
- PCI: 17.176 (em andamento)
- Outras: 2.880

## O que foi feito

### 1. Análise de Estrutura HTML
- ✅ Inspecionado HTML do PCI para descobrir hierarquia
- ✅ Descoberto padrão: `/simulados/categoria/tema` (2 níveis)
- ✅ Encontrados 999 links de simulados
- ✅ Identificadas 42 categorias principais

### 2. Refatoração do Parser
- ✅ Adicionada função `descobrir_subcategorias_do_html()`
- ✅ Melhorada extração de imagens (função `_extrair_todas_imagens()`)
- ✅ Adicionado campo `imagens_urls` (JSONB) para armazenar URLs de imagens
- ✅ Manutenção de compatibilidade com versão anterior

### 3. Schema do Banco de Dados
- ✅ Migração executada com sucesso
- ✅ Colunas adicionadas:
  - `categoria` VARCHAR(255) - categoria do tema
  - `tema` VARCHAR(255) - slug do tema
  - `imagens_urls` JSONB - array de URLs de imagens
  - `subcategoria` VARCHAR(255) - reservada para uso futuro

### 4. Novo Coletor (v2)
- ✅ Criado `coletor_v2.py` com hierarquia completa
- ✅ Suporte a categoria/tema (2 níveis)
- ✅ Integração com checkpoint de progresso
- ✅ Rate limiting: 1-3 segundos entre requisições
- ✅ Scraper rodando em background (iniciado)

### 5. Próximos Passos (Em desenvolvimento)

#### API Endpoints (para criar)
```
GET /api/stats/pci                      - Estatísticas globais do PCI
GET /api/stats/pci/{categoria}          - Breakdown por tema
```

#### Dashboard Hierárquico (para criar)
- Visualização em árvore das categorias → temas
- Indicadores de progresso (coletadas vs esperadas)
- Visualização de imagens associadas
- Gaps por categoria/tema

#### Features Futuras
- [ ] Consolidação de dados duplicados
- [ ] Dashboard com visualização de imagens
- [ ] Endpoints com filtros granulares
- [ ] Relatórios de qualidade de dados
- [ ] Otimização de scraper para 200K+ questões

## Tecnologia Usada

- **Python 3.x** - Scraping e processing
- **BeautifulSoup4** - Parsing HTML
- **PostgreSQL** - Armazenamento
- **FastAPI** - API REST
- **Requests** - HTTP client com retry strategy

## Performance

### Coleta Atual
- Taxa: ~170 questões/minuto (estimado)
- Tempo estimado para 200K: ~20 horas de coleta contínua
- Scraper é resumível via checkpoint

### Qualidade de Dados
- ✅ Todas as questões têm: enunciado, alternativas, matéria
- ✅ 30%+ das questões têm imagens
- ✅ Deduplicação por content_hash

## Estrutura de Dados Coletada

```python
{
    "id_pci": "12345",
    "enunciado": "...",
    "alternativas": {"A": "...", "B": "..."},
    "banca": "Cebraspe",
    "orgao": "PCI",
    "ano": 2023,
    "prova": "Prova 1",
    "materia": "Direito Administrativo",
    "categoria": "direito-administrativo",      # NEW
    "tema": "contratos-administrativos",        # NEW
    "imagens_urls": ["https://...img1.jpg", ...],  # NEW
    "texto_associado": "...",
    "fonte": "pci"
}
```

## Próximas Ações Recomendadas

1. **Aguardar conclusão do scraper** (2-3 horas para coleta completa)
2. **Testar endpoints da API** quando coletada base mínima
3. **Criar dashboard hierárquico** com visualização de gaps
4. **Otimizar rate limiting** se necessário
5. **Consolidar dados** e remover duplicatas

## Contato / Problemas

Se encontrar problemas durante coleta:
- Verificar logs em `pci_coleta_v2.log`
- Testar manualmente endpoints com `monitorar_coleta.py`
- Confirmar conectividade com PostgreSQL

---

**Status:** Em andamento ⏳  
**Última atualização:** 2026-08-17 23:59 UTC
