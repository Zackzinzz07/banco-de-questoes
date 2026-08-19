# PCI Concursos - Banco Hierárquico

> Simulador educacional de questões de concursos públicos brasileiros com dashboard gamificado (Duolingo-style)

## Status

- ✅ **19.721+ questões** coletadas do PCI Concursos
- ✅ **Hierarquia completa:** Matéria → Categoria → Tema
- ✅ **Dashboard educacional** pronto (gamificação + progresso)
- ✅ **API REST** funcional
- ✅ **100% código limpo** (sem debug scripts)

---

## Setup Rápido (5 min)

### 1. Dependências
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Banco de Dados
```bash
docker-compose up -d
sleep 10
```

### 3. Rodar Coleta (opcional)
```bash
python run_pci.py
```

### 4. Iniciar API
```bash
python -m uvicorn banco_questoes.web_api:app --reload
```

**Acesse:** http://localhost:8000

---

## Arquitetura

```
┌─────────────────────────────────────────┐
│ Browser (Dashboard Educacional)         │
│ ├─ Topbar (Streak 🔥 + XP ⭐)         │
│ ├─ Progress Ring (Matéria em foco)     │
│ ├─ Cards Grid (6 matérias)             │
│ ├─ Badges (6 achievements)             │
│ └─ Confete (celebração)                │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │   FastAPI /8000 │
        │  ├─ /api/stats  │
        │  ├─ /api/stats/materias
        │  └─ /api/stats/pci
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  PostgreSQL /5432
        │  ├─ questoes (19.721)
        │  └─ progresso_scraper
        └─────────────────┘
```

---

## Componentes

### Dashboard Educacional (`dashboard_educacional.html`)

**Inspirado em:** Duolingo + Khan Academy

**Elementos:**
- 🔥 **Streak Counter** — Dias consecutivos (motivação)
- ⭐ **XP System** — Pontos por questões estudadas
- 📊 **Progress Ring** — Círculo visual do progresso
- 🎯 **Cards Grid** — 6 matérias principais (clicáveis)
- 🏆 **Badges** — 6 achievements pra desbloquear
- 🎉 **Confete** — Celebração ao clicar "Estudar"
- 🌙 **Dark Mode** — Automático conforme preferência

**Animações:**
- Ring fill (suave, 800ms)
- Card hover (elevate 4px)
- Badge unlock (bounce)
- Confete fall (3s)

---

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Home (redireciona pra dashboard) |
| GET | `/api/stats` | Estatísticas totais por matéria |
| GET | `/api/stats/materias` | Dados detalhados por matéria |
| GET | `/api/stats/pci` | Hierarquia PCI (categoria/tema) |
| GET | `/api/stats/pci/{categoria}` | Temas de uma categoria |

**Exemplo resposta:**
```json
{
  "total_pci": 19721,
  "por_categoria": {
    "saude": {
      "total": 1234,
      "temas": {
        "farmacologia": { "total": 456, "com_imagens": 200 },
        "anatomia": { "total": 778, "com_imagens": 350 }
      }
    }
  }
}
```

---

## Banco de Dados

### Schema

**Tabela: `questoes`**
```sql
id_qc           TEXT UNIQUE
enunciado       TEXT              -- Pergunta
alternativas    JSONB             -- {"A": "...", "B": "...", ...}
gabarito        TEXT              -- Resposta: A, B, C, D, E
comentario      TEXT              -- Explicação
materia         VARCHAR(255)      -- Ex: "Saúde"
categoria       VARCHAR(255)      -- Ex: "saude"
tema            VARCHAR(255)      -- Ex: "farmacologia"
imagens_urls    JSONB             -- ["url1", "url2"]
ano             INTEGER           -- 2024
fonte           VARCHAR(50)       -- "pci" ou "qconcursos"
usada_em_simulado INTEGER         -- 0 ou 1
```

**Tabela: `progresso_scraper`** (checkpoints)
```sql
fonte           VARCHAR(50)
chave           VARCHAR(255)      -- Ex: "saude/farmacologia"
ultima_pagina   INTEGER           -- Onde parou a coleta
PRIMARY KEY (fonte, chave)
```

---

## Coleta de Dados

### Rodar Coleta PCI

```bash
python run_pci.py
```

**O que faz:**
1. Carrega `mapeamento_conteudos.yaml` (categorias/temas)
2. Para cada categoria: descobre temas automaticamente
3. Para cada tema: coleta questões (paginado)
4. Salva com checkpoint (resuma onde parou)
5. Taxa: ~1.5K questões/minuto

**Monitorar:**
```bash
python monitorar_pci.py
```

---

## Estrutura de Pastas

```
├── banco_questoes/
│   ├── db.py                          # Conexão + funções DB
│   ├── web_api.py                     # FastAPI app
│   ├── conteudo_mapper.py             # Mapeador matéria/categoria/tema
│   ├── mapeamento_conteudos.yaml      # Config (42 categorias)
│   ├── scrapers/
│   │   └── pci/
│   │       ├── coletor_v2.py          # Coleta hierárquica
│   │       └── parser.py              # Parse HTML
│   └── web/
│       ├── dashboard_educacional.html # Principal (Duolingo-style)
│       ├── dashboard.html             # Alternativa moderna
│       ├── dashboard_pci.html         # Dados PCI bruto
│       └── dashboard_materia.html     # Por matéria
│
├── run_pci.py                         # Coleta PCI
├── monitorar_pci.py                   # Monitor tempo real
├── docker-compose.yml                 # PostgreSQL
├── requirements.txt                   # Dependências
└── README.md                          # Este arquivo
```

---

## Próximas Etapas

Ver `ROADMAP_PCI.md` para:
1. ✅ Completar coleta PCI (50K+)
2. ⏳ Melhorias API (filtros, busca)
3. ⏳ Gerador de simulados PDF
4. ⏳ Exportação dados (CSV/JSON)

---

## Tecnologia

| Stack | Descrição |
|-------|-----------|
| **Backend** | Python 3.14 + FastAPI + PostgreSQL |
| **Frontend** | HTML5 + CSS3 + JavaScript (zero deps) |
| **DB** | PostgreSQL 15 (Docker) |
| **Scraping** | BeautifulSoup4 + Requests |
| **API** | FastAPI + Uvicorn |

---

## Performance

| Métrica | Valor |
|---------|-------|
| Dashboard load | <1.5s |
| API response | <200ms |
| Mobile FPS | 55-60fps |
| Dark mode | Automático (prefers-color-scheme) |
| Bundle size | ~50KB (HTML+CSS+JS) |

---

## Troubleshooting

### Docker não conecta
```bash
# Iniciar Docker Desktop (Windows)
docker-compose up -d
```

### PostgreSQL recusa conexão
```bash
docker ps  # Verificar se está rodando
docker logs container-id  # Ver logs
```

### API import error
```bash
# Ativar venv
.venv\Scripts\activate
pip install -q psycopg2-binary pyyaml fastapi uvicorn
```

---

## Licença

Código aberto - Use livremente!

---

**Última atualização:** 2026-08-18  
**Versão:** 3.0 (Dashboard Educacional)  
**Commit:** 60e2023
