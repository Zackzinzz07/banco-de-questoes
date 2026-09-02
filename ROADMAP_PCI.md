# Roadmap PCI - Próximas Etapas

## Status Atual

✅ **Coleta funcionando**: 19.721+ questões  
✅ **Hierarquia completa**: Matéria → Categoria → Tema  
✅ **Imagens extraídas**: URLs salvas (JSONB)  
✅ **Checkpoints**: Retoma automaticamente  
✅ **API básica**: GET endpoints funcionando  
✅ **Dashboard**: Mostrando estatísticas  

---

## Próximas Etapas

### 1. Coleta Completa do PCI
- [ ] Expandir categorias faltantes
- [ ] Validar temas para cada categoria
- [ ] Atingir 50K+ questões

**Tempo:** ~2 horas de coleta (contínua)

### 2. Qualidade dos Dados
- [ ] Validar alternativas (sempre 5 opções?)
- [ ] Verificar gabaritos (estão corretos?)
- [ ] Extrair imagens (salvar localmente ou via URLs)
- [ ] Remover duplicatas (se houver)

**Tempo:** 1 dia

### 3. Melhorias na API
- [ ] Endpoint: Filtrar por categoria/tema
- [ ] Endpoint: Buscar texto na questão
- [ ] Endpoint: Gerar simulado por categoria
- [ ] Paginação nos resultados

**Tempo:** 1 dia

### 4. Dashboard Avançado
- [ ] Árvore visual (categoria → tema)
- [ ] Gráficos de distribuição
- [ ] Busca por palavra-chave
- [ ] Exportar para CSV/JSON

**Tempo:** 1-2 dias

### 5. Gerador de Simulados
- [ ] Simulado por matéria
- [ ] Simulado por categoria
- [ ] Simulado por tema
- [ ] PDF com imagens

**Tempo:** 1 dia

---

## Ordem Recomendada

1. **Hoje**: Deixar coleta rodando overnight (19K → 50K)
2. **Amanhã**: Validar qualidade dos dados
3. **Próximos dias**: Melhorias na API
4. **Semana que vem**: Dashboard visual
5. **Depois**: Gerador de PDFs

---

## Comando Rápido

```bash
# Limpar e re-coletar (se precisar)
python run_pci.py

# Monitorar (outro terminal)
python monitorar_pci.py

# API (outro terminal)
python -m uvicorn banco_questoes.web_api:app --reload

# Browser
http://localhost:8000
```

---

## Arquivos para Customizar

| Arquivo | Para |
|---------|------|
| `banco_questoes/mapeamento_conteudos.yaml` | Adicionar categorias/temas |
| `banco_questoes/scrapers/pci/parser.py` | Melhorar parsing |
| `banco_questoes/web_api.py` | Adicionar endpoints |
| `banco_questoes/web/dashboard_pci.html` | Dashboard visual |

---

## Métricas para Monitorar

- **Total de questões**: `SELECT COUNT(*) FROM questoes`
- **Com categoria**: `SELECT COUNT(*) FROM questoes WHERE categoria IS NOT NULL`
- **Com imagens**: `SELECT COUNT(*) FROM questoes WHERE imagens_urls != '[]'`
- **Por categoria**: `SELECT categoria, COUNT(*) FROM questoes GROUP BY categoria`
- **Progress**: Ver `monitorar_pci.py` em tempo real

---

## Próxima Ação

1. Deixar `run_pci.py` rodando
2. Monitorar com `monitorar_pci.py`
3. Quando atingir 50K, fazer validação de qualidade
4. Depois melhorias na API

**Foco:** Quantidade → Qualidade → Funcionalidade
