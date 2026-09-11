/**
 * Banco de Questões — Multi-Banca v2.0
 * Frontend Controller Tablet-First
 */

// Estado Reativo Global
const state = {
    modo: 'edital', // 'edital' | 'materia'
    orgao: '',
    cargo: '',
    materia: '',
    formato: 'certo_errado', // 'certo_errado' | 'multipla_escolha'
    bancaEstilo: 'certo_errado',
    quantidade: 60,
    totalQuestoesEdital: 120,
    pesos: {},
    materiasCargo: [],
    todasMaterias: [],
    concursos: [],
    gerando: false,
    ultimoSimulado: null,
};

// Inicialização ao carregar o DOM
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initModeSwitcher();
    initBancaSelector();
    initQuantityControls();
    initPresetChips();
    initEventListeners();

    // Carga de dados iniciais
    carregarConcursos();
    carregarTodasMaterias();
    carregarSimuladosRecentes();
    verificarConexao();

    // Verificação periódica de conexão (Heartbeat a cada 20s)
    setInterval(verificarConexao, 20000);
});

/* ==========================================================================
   1. Tema Escuro / Claro
   ========================================================================== */
function initTheme() {
    const savedTheme = localStorage.getItem('bq_theme') ||
        (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');

    setTheme(savedTheme);

    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            setTheme(next);
        });
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('bq_theme', theme);
    const icon = document.querySelector('.theme-icon');
    if (icon) {
        icon.textContent = theme === 'dark' ? '🌙' : '☀️';
    }
}

/* ==========================================================================
   2. Verificação de Conexão com Servidor Local
   ========================================================================== */
async function verificarConexao() {
    const statusPill = document.getElementById('connection-status');
    const statusText = statusPill ? statusPill.querySelector('.status-text') : null;

    try {
        const resp = await fetch('/api/stats', { cache: 'no-store' });
        if (resp.ok) {
            if (statusPill) {
                statusPill.className = 'status-pill status-online';
                if (statusText) statusText.textContent = 'Conectado';
            }
        } else {
            throw new Error('Servidor retornou status ' + resp.status);
        }
    } catch {
        if (statusPill) {
            statusPill.className = 'status-pill status-offline';
            if (statusText) statusText.textContent = 'Offline';
        }
    }
}

/* ==========================================================================
   3. Alternância de Modos (Segmented Tabs)
   ========================================================================== */
function initModeSwitcher() {
    const tabEdital = document.getElementById('tab-edital');
    const tabMateria = document.getElementById('tab-materia');
    const secEdital = document.getElementById('section-edital');
    const secMateria = document.getElementById('section-materia');

    function setMode(mode) {
        state.modo = mode;
        if (mode === 'edital') {
            tabEdital.classList.add('active');
            tabEdital.setAttribute('aria-selected', 'true');
            tabMateria.classList.remove('active');
            tabMateria.setAttribute('aria-selected', 'false');

            secEdital.style.display = 'block';
            secMateria.style.display = 'none';

            // Ajusta quantidade para o edital
            if (state.totalQuestoesEdital) {
                atualizarQuantidade(Math.min(state.quantidade || 60, state.totalQuestoesEdital));
            }
        } else {
            tabMateria.classList.add('active');
            tabMateria.setAttribute('aria-selected', 'true');
            tabEdital.classList.remove('active');
            tabEdital.setAttribute('aria-selected', 'false');

            secMateria.style.display = 'block';
            secEdital.style.display = 'none';

            if (!state.materia && state.todasMaterias.length > 0) {
                const matSelect = document.getElementById('materia-select');
                if (matSelect && matSelect.value) {
                    state.materia = matSelect.value;
                }
            }
        }
        atualizarResumo();
    }

    if (tabEdital) tabEdital.addEventListener('click', () => setMode('edital'));
    if (tabMateria) tabMateria.addEventListener('click', () => setMode('materia'));
}

/* ==========================================================================
   4. Seletor de Formato Universal (Cards Visuais)
   ========================================================================== */
function normalizarFormato(val) {
    if (!val) return 'certo_errado';
    const norm = String(val).toLowerCase().trim();
    if (norm === 'cebraspe' || norm === 'cespe' || norm.includes('certo') || norm === 'julgar') {
        return 'certo_errado';
    }
    return 'multipla_escolha';
}

function selecionarFormato(formatoNome) {
    const formatoFinal = normalizarFormato(formatoNome);
    const cards = document.querySelectorAll('.formato-card, .banca-card');
    const selectLegado = document.getElementById('banca');

    cards.forEach(card => {
        const val = card.dataset.formato || card.dataset.banca;
        const normVal = normalizarFormato(val);
        const match = normVal === formatoFinal;
        card.classList.toggle('active', match);
        const radio = card.querySelector('input[type="radio"]');
        if (radio) radio.checked = match;
    });

    state.formato = formatoFinal;
    state.bancaEstilo = formatoFinal === 'certo_errado' ? 'cebraspe' : 'aocp';
    if (selectLegado) selectLegado.value = state.bancaEstilo;
    atualizarResumo();
}

function selecionarBanca(bancaNome) {
    selecionarFormato(bancaNome);
}

function initBancaSelector() {
    const cards = document.querySelectorAll('.formato-card, .banca-card');
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const fmt = card.dataset.formato || card.dataset.banca;
            selecionarFormato(fmt);
        });
    });
}

/* ==========================================================================
   5. Controle de Quantidade (Slider Tátil + Input + Display)
   ========================================================================== */
function initQuantityControls() {
    const slider = document.getElementById('quantidade-slider');
    const display = document.getElementById('display-quantidade');
    const inputHidden = document.getElementById('quantidade');

    if (slider) {
        slider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            atualizarQuantidade(val, false);
        });
    }

    if (inputHidden) {
        inputHidden.addEventListener('change', (e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val > 0) {
                atualizarQuantidade(val, true);
            }
        });
    }
}

function atualizarQuantidade(val, syncSlider = true) {
    state.quantidade = val;
    const display = document.getElementById('display-quantidade');
    const slider = document.getElementById('quantidade-slider');
    const inputHidden = document.getElementById('quantidade');

    if (display) display.textContent = val;
    if (inputHidden) inputHidden.value = val;
    if (syncSlider && slider) slider.value = val;

    atualizarResumo();
}

/* ==========================================================================
   6. Chips de Presets (Proporção do Edital & Metas Rápidas)
   ========================================================================== */
function initPresetChips() {
    // Modo Edital
    const chipsEdital = document.querySelectorAll('#preset-proporcao-group .chip');
    chipsEdital.forEach(chip => {
        chip.addEventListener('click', () => {
            chipsEdital.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            const total = state.totalQuestoesEdital || 120;
            if (chip.dataset.ratio) {
                const ratio = parseFloat(chip.dataset.ratio);
                const qtd = Math.round(total * ratio);
                atualizarQuantidade(qtd);
            } else if (chip.dataset.fixed) {
                const fixed = parseInt(chip.dataset.fixed, 10);
                atualizarQuantidade(fixed);
            }
        });
    });

    // Modo Matéria
    const chipsMateria = document.querySelectorAll('#section-materia .preset-chips .chip');
    chipsMateria.forEach(chip => {
        chip.addEventListener('click', () => {
            chipsMateria.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            const qtd = parseInt(chip.dataset.qtd, 10);
            if (!isNaN(qtd)) {
                atualizarQuantidade(qtd);
            }
        });
    });
}

/* ==========================================================================
   7. Carga de Editais e Cargos
   ========================================================================== */
async function carregarConcursos() {
    const selectOrgao = document.getElementById('orgao');
    const filtroConcurso = document.getElementById('filtro-concurso-materia');

    try {
        const resp = await fetch('/api/orgaos');
        if (!resp.ok) throw new Error('Falha ao obter concursos');
        const data = await resp.json();

        state.concursos = data.orgaos || [];

        // Preenche select do Edital
        selectOrgao.innerHTML = '<option value="">-- Escolha um Concurso / Edital --</option>';
        state.concursos.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = formatarNomeConcurso(c);
            selectOrgao.appendChild(opt);
        });

        // Preenche filtro do Modo Matéria
        if (filtroConcurso) {
            filtroConcurso.innerHTML = '<option value="todas">Todas as 53 matérias do acervo geral</option>';
            state.concursos.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = `Apenas matérias do edital: ${formatarNomeConcurso(c)}`;
                filtroConcurso.appendChild(opt);
            });
        }

        // Seleciona PMDF por padrão se existir
        if (state.concursos.includes('pmdf')) {
            selectOrgao.value = 'pmdf';
            onOrgaoChange('pmdf');
        }
    } catch (erro) {
        console.error('Erro ao carregar editais:', erro);
        showToast('Não foi possível carregar editais. Verifique a conexão.', 'error');
    }
}

function formatarNomeConcurso(slug) {
    const mapa = {
        pmdf: 'PMDF (Polícia Militar do DF)',
        prf: 'PRF (Polícia Rodoviária Federal)',
        inss: 'INSS (Técnico e Analista)',
        sedes_df: 'SEDES/DF (Secretaria de Des. Social)',
        bacen: 'BACEN (Banco Central)',
        pcdf: 'PCDF (Polícia Civil do DF)',
        cbmdf: 'CBMDF (Corpo de Bombeiros)',
    };
    return mapa[slug.toLowerCase()] || slug.toUpperCase().replace(/_/g, ' ');
}

async function onOrgaoChange(orgao) {
    state.orgao = orgao;
    state.cargo = '';
    state.pesos = {};

    const selectCargo = document.getElementById('cargo');
    const cargoGroup = document.getElementById('cargo-group');
    const presetGroup = document.getElementById('preset-proporcao-group');

    selectCargo.innerHTML = '<option value="">Carregando cargos do edital...</option>';
    cargoGroup.style.display = orgao ? 'block' : 'none';
    if (presetGroup) presetGroup.style.display = 'none';

    if (!orgao) {
        atualizarResumo();
        return;
    }

    try {
        const resp = await fetch(`/api/cargos/${orgao}`);
        if (!resp.ok) throw new Error('Falha ao obter cargos');
        const data = await resp.json();

        selectCargo.innerHTML = '';
        const cargos = data.cargos || [];

        cargos.forEach((cargo, idx) => {
            const opt = document.createElement('option');
            opt.value = cargo;
            opt.textContent = cargo;
            selectCargo.appendChild(opt);
        });

        if (cargos.length > 0) {
            selectCargo.value = cargos[0];
            onCargoChange(orgao, cargos[0]);
        }
    } catch (erro) {
        console.error('Erro ao carregar cargos:', erro);
        selectCargo.innerHTML = '<option value="">Erro ao carregar cargos</option>';
        showToast(`Erro ao carregar cargos de ${orgao.toUpperCase()}`, 'error');
    }
}

async function onCargoChange(orgao, cargo) {
    state.cargo = cargo;
    const presetGroup = document.getElementById('preset-proporcao-group');

    if (!cargo) {
        atualizarResumo();
        return;
    }

    try {
        const resp = await fetch(`/api/materias/${orgao}/${encodeURIComponent(cargo)}`);
        if (!resp.ok) throw new Error('Falha ao obter matérias e pesos');
        const data = await resp.json();

        state.pesos = data.pesos || {};
        state.materiasCargo = data.materias || [];
        state.totalQuestoesEdital = data.total_questoes || 120;
        state.bancaOficial = data.banca || '';
        const editalFmt = (data.formato || '').toLowerCase();
        if (editalFmt.includes('certo') || (state.bancaOficial && state.bancaOficial.toLowerCase().includes('cebraspe'))) {
            selecionarFormato('certo_errado');
        } else {
            selecionarFormato('multipla_escolha');
        }

        // Atualiza textos dos chips
        const chip100Val = document.getElementById('chip-100-val');
        const chip50Val = document.getElementById('chip-50-val');
        if (chip100Val) chip100Val.textContent = `${state.totalQuestoesEdital} questões`;
        if (chip50Val) chip50Val.textContent = `${Math.round(state.totalQuestoesEdital / 2)} questões`;

        if (presetGroup) presetGroup.style.display = 'block';

        // Atualiza slider maximo para cobrir até a prova oficial
        const slider = document.getElementById('quantidade-slider');
        if (slider) {
            slider.max = Math.max(120, state.totalQuestoesEdital);
        }

        // Compatibilidade com testes unitários/Playwright existentes
        atualizarStatsCompatibilidade(data);

        atualizarResumo();
    } catch (erro) {
        console.error('Erro ao carregar matérias do cargo:', erro);
        showToast('Erro ao obter dados do edital para o cargo selecionado.', 'error');
    }
}

function atualizarStatsCompatibilidade(data) {
    const statsSection = document.getElementById('stats-section');
    const statsTitle = document.getElementById('stats-title');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const statsList = document.getElementById('stats-list');

    if (statsSection) statsSection.style.display = 'block';
    if (statsTitle) statsTitle.textContent = `${data.orgao.toUpperCase()} - ${data.cargo}`;
    if (progressFill) progressFill.style.width = '100%';
    if (progressText) progressText.textContent = `${data.total_questoes} questões mapeadas`;
    if (statsList) {
        statsList.innerHTML = Object.entries(data.pesos || {})
            .map(([m, p]) => `<div>${m}: ${p} questões</div>`)
            .join('');
    }
}

/* ==========================================================================
   8. Carga de Matérias (Modo Específico)
   ========================================================================== */
async function carregarTodasMaterias() {
    const select = document.getElementById('materia-select');
    try {
        const resp = await fetch('/api/materias/todas');
        if (!resp.ok) throw new Error('Falha ao carregar matérias');
        const lista = await resp.json();

        state.todasMaterias = lista || [];
        popularSelectMaterias(state.todasMaterias);

        // Preenche com primeira matéria
        if (state.todasMaterias.length > 0 && select) {
            select.value = state.todasMaterias.includes('Informática') ? 'Informática' : state.todasMaterias[0];
            state.materia = select.value;
        }
    } catch (erro) {
        console.error('Erro ao carregar matérias gerais:', erro);
        // Fallback para endpoint antigo
        try {
            const resp2 = await fetch('/api/materias');
            const lista2 = await resp2.json();
            state.todasMaterias = lista2 || [];
            popularSelectMaterias(state.todasMaterias);
        } catch {
            select.innerHTML = '<option value="">Erro ao carregar matérias</option>';
        }
    }
}

function popularSelectMaterias(materias) {
    const select = document.getElementById('materia-select');
    if (!select) return;

    select.innerHTML = '<option value="">-- Escolha uma Matéria --</option>';
    materias.forEach(mat => {
        const opt = document.createElement('option');
        opt.value = mat;
        opt.textContent = mat;
        select.appendChild(opt);
    });
}

/* ==========================================================================
   9. Atualização do Resumo Visual ao Vivo (Coluna Direita)
   ========================================================================== */
function atualizarResumo() {
    const summaryModo = document.getElementById('summary-modo');
    const summaryBanca = document.getElementById('summary-banca');
    const summaryTotal = document.getElementById('summary-total');
    const summaryFormato = document.getElementById('summary-formato');
    const distCount = document.getElementById('dist-disciplinas-count');
    const container = document.getElementById('distribuicao-container');

    const nomesBanca = {
        cebraspe: 'Cebraspe',
        aocp: 'AOCP',
        fgv: 'FGV',
        iades: 'IADES',
    };

    if (summaryBanca) {
        summaryBanca.textContent = state.formato === 'certo_errado' ? 'Cebraspe (C/E)' : 'Universal (A-E)';
    }
    if (summaryFormato) {
        summaryFormato.textContent = state.formato === 'certo_errado' 
            ? 'Certo / Errado' 
            : 'Múltipla Escolha';
    }
    if (summaryTotal) summaryTotal.textContent = `${state.quantidade} questões`;

    if (state.modo === 'edital') {
        if (summaryModo) summaryModo.textContent = state.orgao ? state.orgao.toUpperCase() : 'Edital Oficial';

        const disciplinas = Object.entries(state.pesos);
        if (distCount) distCount.textContent = `${disciplinas.length} matérias no edital`;

        if (disciplinas.length === 0) {
            container.innerHTML = '<p class="placeholder-text">Selecione um concurso e cargo para visualizar a proporção do edital.</p>';
            return;
        }

        const totalPesos = disciplinas.reduce((acc, [, peso]) => acc + peso, 0) || 1;
        const totalAlvo = state.quantidade;

        container.innerHTML = disciplinas.map(([materia, peso]) => {
            const proporcao = peso / totalPesos;
            const qtdEstimada = Math.round(proporcao * totalAlvo);
            const pct = Math.round(proporcao * 100);

            return `
                <div class="dist-bar-item">
                    <div class="dist-bar-info">
                        <span class="dist-bar-name">${materia}</span>
                        <span class="dist-bar-val">${qtdEstimada}q (${pct}%)</span>
                    </div>
                    <div class="dist-progress-bg">
                        <div class="dist-progress-fill" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        if (summaryModo) summaryModo.textContent = 'Treino por Matéria';
        if (distCount) distCount.textContent = '1 matéria selecionada';

        const materiaNome = state.materia || 'Nenhuma matéria selecionada';
        container.innerHTML = `
            <div class="dist-bar-item">
                <div class="dist-bar-info">
                    <span class="dist-bar-name">🎯 ${materiaNome}</span>
                    <span class="dist-bar-val">${state.quantidade}q (100%)</span>
                </div>
                <div class="dist-progress-bg">
                    <div class="dist-progress-fill" style="width: 100%; background: linear-gradient(90deg, #10b981 0%, #34d399 100%);"></div>
                </div>
            </div>
        `;
    }
}

/* ==========================================================================
   10. Geração do Simulado em PDF (POST /api/v2/simulado/gerar)
   ========================================================================== */
function initEventListeners() {
    // Selects
    const selectOrgao = document.getElementById('orgao');
    if (selectOrgao) {
        selectOrgao.addEventListener('change', (e) => onOrgaoChange(e.target.value));
    }

    const selectCargo = document.getElementById('cargo');
    if (selectCargo) {
        selectCargo.addEventListener('change', (e) => onCargoChange(state.orgao, e.target.value));
    }

    const selectMateria = document.getElementById('materia-select');
    if (selectMateria) {
        selectMateria.addEventListener('change', (e) => {
            state.materia = e.target.value;
            atualizarResumo();
        });
    }

    const filtroConcurso = document.getElementById('filtro-concurso-materia');
    if (filtroConcurso) {
        filtroConcurso.addEventListener('change', async (e) => {
            const val = e.target.value;
            if (val === 'todas') {
                popularSelectMaterias(state.todasMaterias);
            } else {
                try {
                    const resp = await fetch(`/api/cargos/${val}`);
                    const data = await resp.json();
                    if (data.cargos && data.cargos[0]) {
                        const mResp = await fetch(`/api/materias/${val}/${encodeURIComponent(data.cargos[0])}`);
                        const mData = await mResp.json();
                        popularSelectMaterias(mData.materias || state.todasMaterias);
                    }
                } catch {
                    popularSelectMaterias(state.todasMaterias);
                }
            }
        });
    }

    // Botão de Geração
    const btnGerar = document.getElementById('btn-gerar');
    if (btnGerar) {
        btnGerar.addEventListener('click', executarGeracaoSimulado);
    }

    // Botão de Atualizar Recentes
    const btnRefresh = document.getElementById('btn-atualizar-recentes');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', carregarSimuladosRecentes);
    }
}

async function executarGeracaoSimulado() {
    if (state.gerando) return;

    // Validações
    if (state.modo === 'edital') {
        if (!state.orgao) {
            showToast('Por favor, selecione o concurso / edital.', 'error');
            return;
        }
        if (!state.cargo) {
            showToast('Por favor, selecione um cargo para o edital.', 'error');
            return;
        }
    } else {
        if (!state.materia) {
            showToast('Por favor, selecione uma matéria para treino.', 'error');
            return;
        }
    }

    const btnGerar = document.getElementById('btn-gerar');
    const deliveryCard = document.getElementById('delivery-card');
    const lacunasAlert = document.getElementById('lacunas-alert');

    // UI State: Gerando
    state.gerando = true;
    btnGerar.disabled = true;
    btnGerar.innerHTML = '<div class="mini-spinner"></div><span>Diagramando simulado em PDF...</span>';

    const payload = {
        modo: state.modo,
        concurso: state.orgao || null,
        cargo: state.cargo || null,
        materia: state.materia || null,
        banca_estilo: state.formato,
        formato: state.formato,
        quantidade: state.quantidade,
    };

    try {
        const resp = await fetch('/api/v2/simulado/gerar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            let msgErro = `Erro ${resp.status}`;
            try {
                const errData = await resp.json();
                msgErro = errData.detail || msgErro;
            } catch {}
            throw new Error(msgErro);
        }

        const data = await resp.json();
        state.ultimoSimulado = data;

        // Exibe Delivery Card
        if (deliveryCard) {
            const filenameEl = document.getElementById('delivery-filename');
            const btnAbrir = document.getElementById('btn-abrir-pdf');
            const btnBaixar = document.getElementById('btn-baixar-pdf');

            if (filenameEl) filenameEl.textContent = data.arquivo;

            if (btnAbrir) {
                btnAbrir.onclick = () => {
                    window.open(`${data.url_download}?inline=true`, '_blank');
                };
            }

            if (btnBaixar) {
                btnBaixar.href = data.url_download;
                btnBaixar.setAttribute('download', data.arquivo);
            }

            deliveryCard.style.display = 'block';
            deliveryCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Exibe Transparência de Lacunas (se houver)
        if (lacunasAlert) {
            const lacunas = data.lacunas || {};
            const lacunasList = document.getElementById('lacunas-list');
            const lacunasMsg = document.getElementById('lacunas-msg');

            const itensLacunas = Object.entries(lacunas);
            if (itensLacunas.length > 0) {
                const totalFaltam = itensLacunas.reduce((acc, [, q]) => acc + q, 0);
                if (lacunasMsg) {
                    lacunasMsg.textContent = `Simulado gerado com ${data.questoes_geradas} questões. Aviso: ${totalFaltam} questões não foram encontradas no acervo e NÃO foram substituídas por matérias incorretas.`;
                }
                if (lacunasList) {
                    lacunasList.innerHTML = itensLacunas
                        .map(([m, q]) => `<li><strong>${m}:</strong> faltam ${q} questões</li>`)
                        .join('');
                }
                lacunasAlert.style.display = 'block';
            } else {
                lacunasAlert.style.display = 'none';
            }
        }

        showToast(`Simulado gerado com sucesso! (${data.questoes_geradas} questões)`, 'success');
        carregarSimuladosRecentes();
    } catch (erro) {
        console.error('Erro na geração:', erro);
        showToast(`Falha na geração: ${erro.message}`, 'error');
    } finally {
        state.gerando = false;
        btnGerar.disabled = false;
        btnGerar.innerHTML = '<span class="btn-icon">⚡</span><span class="btn-label">Gerar Simulado em PDF</span>';
    }
}

/* ==========================================================================
   11. Carga de Simulados Recentes no Dispositivo
   ========================================================================== */
async function carregarSimuladosRecentes() {
    const container = document.getElementById('lista-simulados-recentes');
    if (!container) return;

    try {
        const resp = await fetch('/api/simulados/recentes');
        if (!resp.ok) throw new Error('Falha ao obter recentes');
        const lista = await resp.json();

        if (!lista || lista.length === 0) {
            container.innerHTML = '<p class="placeholder-text">Nenhum simulado gerado ainda. Crie o seu primeiro simulado acima!</p>';
            return;
        }

        container.innerHTML = lista.map(item => {
            const dataFmt = formatarTimestamp(item.data);
            const downloadUrl = `/api/simulados/download/${encodeURIComponent(item.nome)}`;

            return `
                <div class="recent-item">
                    <div class="recent-item-left">
                        <span class="recent-pdf-icon">📄</span>
                        <div class="recent-info">
                            <div class="recent-name" title="${item.nome}">${item.nome}</div>
                            <div class="recent-meta">
                                <span class="recent-size-badge">${item.tamanho_kb} KB</span>
                                <span>${dataFmt}</span>
                            </div>
                        </div>
                    </div>
                    <div class="recent-actions">
                        <button type="button" class="btn-open-chip" onclick="window.open('${downloadUrl}?inline=true', '_blank')">
                            Abrir
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (erro) {
        console.error('Erro ao listar recentes:', erro);
        container.innerHTML = '<p class="placeholder-text" style="color:#ef4444;">Erro ao carregar simulados recentes.</p>';
    }
}

function formatarTimestamp(segundos) {
    if (!segundos) return '';
    const d = new Date(segundos * 1000);
    const hoje = new Date();
    const ehHoje = d.toDateString() === hoje.toDateString();

    const hora = d.getHours().toString().padStart(2, '0');
    const min = d.getMinutes().toString().padStart(2, '0');

    if (ehHoje) {
        return `Hoje às ${hora}:${min}`;
    }
    const dia = d.getDate().toString().padStart(2, '0');
    const mes = (d.getMonth() + 1).toString().padStart(2, '0');
    return `${dia}/${mes} às ${hora}:${min}`;
}

/* ==========================================================================
   12. Notificações Toast
   ========================================================================== */
function showToast(mensagem, tipo = 'info', duracao = 4500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;

    const icon = tipo === 'error' ? '⚠️' : tipo === 'success' ? '✅' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${mensagem}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duracao);
}
