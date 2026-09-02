# Dashboard Design - PCI Concursos

## Cores Principais

### Paleta Escolhida: **Moderno Indigo-Violet-Amber**

```
Primary:   #6366f1 (Indigo) - Botões, acentos principais
Secondary: #8b5cf6 (Violet) - Gradientes, destaques
Accent:    #f59e0b (Amber)  - Alertas, números importantes
Success:   #10b981 (Green)  - Badges, confirmações
```

**Por que essas cores?**
- ✅ Profissional e moderno
- ✅ Alto contraste (acessibilidade)
- ✅ Agradável para uso prolongado
- ✅ Funciona bem em tema escuro e claro

---

## Componentes

### 1. Header
- **Fundo:** Gradiente Indigo → Violet
- **Altura:** 60-80px
- **Tipografia:** Título grande (2.5em) + Subtítulo descritivo

### 2. Stats Cards (KPI)
- **Layout:** Grid responsivo (4 colunas em desktop, 1 em mobile)
- **Estilo:** Fundo branco, borda esquerda colorida
- **Hover:** Levanta 5px + Sombra aumenta
- **Cores das bordas:**
  - Card 1: Indigo (Total)
  - Card 2: Violet (Categorias)
  - Card 3: Amber (Temas)
  - Card 4: Green (Com imagens)

### 3. Main Cards (Categorias + Top 10)
- **Fundo:** Branco puro
- **Sombra:** 0 4px 6px rgba(0,0,0,0.07)
- **Raio:** 12px (smooth)
- **Título:** Com barra vertical colorida

### 4. Search Box
- **Border:** 2px solid slate-200
- **Focus:** Muda pra indigo + shadow azul
- **Transição:** Suave (0.3s)

### 5. Category Items
- **Layout:** Flex com nome + count
- **Hover:** Fundo mais claro + TranslateX +5px
- **Progress bar:** Gradiente indigo→violet

### 6. Materias Chart
- **Estilo:** Horizontal bars com gradiente
- **Cores variadas:** 5 gradientes diferentes em loop
- **Max height:** Responsivo

---

## Responsividade

```
Desktop (>1024px):   2 colunas em main-grid
Tablet (768-1024px): 1.5 colunas
Mobile (<768px):     1 coluna, full width
```

---

## Animações

| Elemento | Animação | Duração |
|----------|----------|---------|
| Cards | Scale + Shadow | 0.3s ease |
| Buttons | Scale + Glow | 0.3s ease |
| Progress | Width change | 0.3s ease |
| Inputs | Border + Shadow | 0.3s ease |
| Spinner | Rotation | 1s infinite |

---

## Tipografia

```
Fonts: Segoe UI, Tahoma, Geneva, Verdana, sans-serif

h1: 2.5em, font-weight: 700
h2: 1.5em, font-weight: 600
Body: 1em, color: #1e293b
Label: 0.9em, uppercase, weight: 600
```

---

## Dark Mode (Futuro)

Se adicionar dark mode depois:
```css
:root[data-theme="dark"] {
    --bg-dark: #0f172a
    --bg-light: #1e293b
    --text-dark: #f1f5f9
    --text-light: #94a3b8
}
```

---

## Acessibilidade

✅ Contraste WCAG AA (4.5:1 mínimo)  
✅ Focusable elementos (tab navigation)  
✅ Sem dependência de cor apenas  
✅ Scrollbar customizado  
✅ Responsivo para mobile  

---

## Customizações Possíveis

Se quiser mudar:

1. **Mudar paleta de cores:**
   - Edit `:root` variables no `<style>`

2. **Adicionar logo:**
   - Add `<img>` no header

3. **Mudar fonte:**
   - Edit `font-family` no body

4. **Adicionar tema claro:**
   - Duplicate `:root` com vars claras

5. **Adicionar gráficos:**
   - Usar Chart.js ou similar

---

## Performance

- 📦 Zero dependências externas
- 🚀 CSS puro (sem frameworks)
- 💾 HTML + CSS + JS inline
- ⚡ Atualiza API a cada 30s
- 📱 Mobile-first design

---

**Status:** ✅ Pronto para produção  
**Última atualização:** 2026-08-18  
**Versão:** 1.0
