# Plano: Coleta Multi-Fonte (PRF, BACEN, QConcursos, Quadrix, etc)

## Status Atual ✅

- ✅ **PCI:** 27.918 questões (re-coletando com categoria/tema)
- ✅ **SEDES/DF:** 10.170 questões (consolidado)
- ✅ **Infraestrutura:** API + Dashboard pronto
- ✅ **Schema:** Pronto para múltiplas fontes

---

## Fontes Disponíveis

### 1. QConcursos (federal exams)
**Arquivo:** `scraper_qc.py`  
**Status:** Pronto  
**Exames:** PRF, BACEN, Receita Federal, INSS, Correios, Banco do Brasil  
**Estimado:** ~50K+ questões

```bash
python scraper_qc.py
```

### 2. Instituto Quadrix
**Arquivo:** `coletor_quadrix.py`  
**Status:** Pronto  
**Estimado:** ~5K questões

```bash
python coletor_quadrix.py
```

### 3. PCI Concursos
**Arquivo:** `banco_questoes/scrapers/pci/coletor_v2.py`  
**Status:** RE-coletando com correção  
**Estimado:** 27.918 questões

```bash
python -m banco_questoes.scrapers.pci.coletor_v2
```

---

## Plano de Execução

### Fase 1: Coleta Paralela (HOJE)

```bash
# Terminal 1: PCI (járodando)
# Terminal 2: QConcursos
python scraper_qc.py

# Terminal 3: Quadrix
python coletor_quadrix.py
```

**Tempo estimado:** 2-3 horas para coleta completa  
**Total esperado:** ~75K questões

### Fase 2: Consolidação (AMANHÃ)

1. Verificar deduplicação (content_hash)
2. Normalizar matérias entre fontes
3. Atualizar dashboard com filtro por fonte
4. Gerar relatório de cobertura

### Fase 3: Dashboard Aprimorado (FUTURO)

```
Dashboard v2:
├─ Filtro por fonte (PCI, QConcursos, Quadrix)
├─ Estatísticas por fonte
├─ Cobertura de matérias por exame
└─ Simulados específicos por exame
```

---

## Estrutura de Dados por Fonte

```json
{
  // PCI - Órgãos públicos (prefeituras, etc)
  "fonte": "pci",
  "categoria": "direito-administrativo",
  "tema": "contratos-administrativos",
  "orgao": "Prefeitura XYZ",
  
  // QConcursos - Exames federais
  "fonte": "qconcursos",
  "categoria": null,
  "tema": null,
  "orgao": "PRF",  // ou BACEN, Receita Federal, etc
  
  // Quadrix - Instituto organizador
  "fonte": "quadrix",
  "categoria": "conhecimentos-gerais",
  "tema": "direito-administrativo",
  "orgao": "Instituto Quadrix"
}
```

---

## Monitorar Coleta

```bash
# Terminal separado: monitorar progresso
while true; do
  python monitorar_coleta.py
  sleep 10
done
```

Esperado:
```
Total: 75.000+ questoes
├─ PCI:        27.918 qs
├─ QConcursos: 50.000 qs  
└─ Quadrix:     5.000 qs
```

---

## Próximos Passos

- [ ] Rodar coleta multi-fonte em paralelo
- [ ] Monitorar progresso (30min-2h)
- [ ] Validar deduplicação (content_hash)
- [ ] Atualizar dashboard com filtro por fonte
- [ ] Gerar report de cobertura por matéria/exame

---

## Tempo Total Estimado

| Fase | Tempo | Status |
|------|-------|--------|
| PCI (re-coleta) | 30-45 min | ⏳ Em andamento |
| QConcursos | 45-60 min | 🔲 Pendente |
| Quadrix | 15-20 min | 🔲 Pendente |
| **Total** | **2-3 horas** | 🔲 |

---

**Quer começar agora?** 🚀

```bash
# 1. Verifique scraper_qc.py (check imports/conectividade)
# 2. Rode em paralelo com PCI
# 3. Monitor progresso
```
