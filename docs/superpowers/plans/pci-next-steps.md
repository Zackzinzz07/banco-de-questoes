# PCI Concursos - Próximas Etapas

> **Para agentic workers:** Use superpowers:subagent-driven-development para executar este plano task-by-task.

**Goal:** Expandir PCI Concursos de 19K para 50K+ questões, com API robusta e gerador de simulados.

**Architecture:** 4 etapas independentes que podem rodar em paralelo (exceto Etapa 3 que depende de dados da API).

**Tech Stack:** Python 3.14, FastAPI, PostgreSQL, ReportLab, Zero dependências frontend.

---

## Global Constraints

- **Banco:** PostgreSQL (Docker)
- **Coleta:** Rate limit 1-3s entre requests
- **Checkpoint:** Sempre salvar progresso
- **API:** Endpoints sem autenticação (backend interno)
- **Dashboard:** Sem dependências externas (CSS+JS inline)
- **PDFs:** ReportLab, sem bibliotecas de design

---

## Etapa 1: Completar Coleta PCI (50K+)

**Escopo:** Expandir categorias/temas, validar dados, atingir 50K questões.

**Tempo estimado:** 8-12 horas (4-6 de coleta automática + 2-3 de validação)

**Dependências:** Nenhuma (paralelo com tudo)

**Entregáveis:**
- [ ] Expandir mapeamento_conteudos.yaml com 100% das categorias PCI
- [ ] Validar temas por categoria (sem gaps)
- [ ] Rodar coleta completa (19K → 50K)
- [ ] Validar alternativas (5 opções? gabarito presente?)
- [ ] Relatório de distribuição final

**Prioridade:** 🔴 ALTA - Mais dados = melhor base

---

## Etapa 2: API com Filtros + Busca

**Escopo:** Endpoints avançados pra explorar dados.

**Tempo estimado:** 3-4 horas (API + testes)

**Dependências:** Etapa 1 (dados completos)

**Entregáveis:**
- [ ] GET `/api/questoes?materia=X&categoria=Y&tema=Z` - Filtro hierárquico
- [ ] GET `/api/questoes/busca?texto=...` - Busca full-text
- [ ] GET `/api/questoes/{id}` - Detalhe com imagens
- [ ] GET `/api/categorias/{cat}/estatisticas` - Deep stats
- [ ] Testes de cada endpoint

**Prioridade:** 🟡 MEDIA - Necessário pra funcionalmente usar dados

---

## Etapa 3: Gerador de Simulados PDF

**Escopo:** Gerar PDFs de questões por categoria/tema.

**Tempo estimado:** 5-6 horas (PDF + design + testes)

**Dependências:** Etapa 2 (API de filtro)

**Entregáveis:**
- [ ] POST `/api/simulado/categoria/{cat}` - Gerar PDF por categoria
- [ ] POST `/api/simulado/tema/{cat}/{tema}` - Gerar PDF por tema
- [ ] Design PDF: 2 colunas, imagens, gabarito
- [ ] Cache de PDFs gerados
- [ ] Endpoint de download

**Prioridade:** 🟡 MEDIA - Funcionalidade user-facing importante

---

## Etapa 4: Exportação Dados (CSV/JSON)

**Escopo:** Exportar dados para outros formatos.

**Tempo estimado:** 2-3 horas (exportação + testes)

**Dependências:** Etapa 1 ou 2

**Entregáveis:**
- [ ] GET `/api/export/csv?materia=X` - CSV com questões
- [ ] GET `/api/export/json?categoria=Y` - JSON estruturado
- [ ] Suporte a compressão (ZIP)
- [ ] Validação de dados exportados

**Prioridade:** 🟢 BAIXA - Bônus, não essencial

---

## Ordem Recomendada

### **Semana 1:**
1. **Etapa 1** (Coleta) - Rodar overnight, validar dados
2. **Etapa 2** (API) - Em paralelo, começar simples (filtro básico)

### **Semana 2:**
3. **Etapa 3** (PDFs) - Com dados completos + API pronta
4. **Etapa 4** (Exportação) - Quando tiver tempo

---

## Timeline Total

| Etapa | Tempo | Paralelo? | Start |
|-------|-------|-----------|-------|
| 1. Coleta | 8-12h | Sim | Agora |
| 2. API | 3-4h | Com 1 | +6h |
| 3. PDFs | 5-6h | Depois de 2 | +12h |
| 4. Export | 2-3h | Depois | +20h |
| **Total** | **18-25h** | ~30h wallclock | - |

**Com paralelização:** ~30 horas wallclock (3-4 dias úteis)

---

## Métricas de Sucesso

- ✅ 50K+ questões no banco
- ✅ Todas com categoria/tema preenchidos
- ✅ API respondendo em <200ms
- ✅ Dashboard mostrando corretamente
- ✅ PDF gerado em <5 segundos
- ✅ 100% cobertura de testes

---

## Decisões

**P1: Fazer as 4 etapas ou só 1-3?**
- Recomendação: **Todas** (30h total é viável)
- Alternativa: 1-3 (18h) e deixar exportação pra depois

**P2: Fazer etapa 4 ou focar em qualidade das 3 primeiras?**
- Recomendação: **Qualidade das 3 primeiras** (P2 usa os mesmos dados)

**P3: Quando começar?**
- **Agora!** Coleta roda em background, tudo pronto

---

## Próximo Passo

1. Confirmar qual etapas fazer (todas 4 ou 1-3?)
2. Iniciar **Etapa 1** (coleta 19K → 50K)
3. Usar subagent-driven-development pra executar com reviews

**Pronto?** Quer que eu execute o plano agora?
