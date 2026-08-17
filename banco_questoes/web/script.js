let estadoAtual = {
    orgao: null,
    cargo: null,
    materias: {},
    pesos: {},
};

// Load órgãos on page load
document.addEventListener('DOMContentLoaded', () => {
    carregarPainelGeral();
    carregarPainelPCI();
    carregarOrgaos();
});

async function carregarOrgaos() {
    try {
        const resp = await fetch('/api/orgaos');
        const data = await resp.json();

        const select = document.getElementById('orgao');
        data.orgaos.forEach(orgao => {
            const option = document.createElement('option');
            option.value = orgao;
            option.textContent = orgao.toUpperCase().replace(/_/g, ' ');
            select.appendChild(option);
        });

        select.addEventListener('change', () => onOrgaoChange(select.value));
    } catch (erro) {
        console.error('Erro ao carregar órgãos:', erro);
    }
}

async function onOrgaoChange(orgao) {
    estadoAtual.orgao = orgao;
    estadoAtual.cargo = null;

    const cargoSelect = document.getElementById('cargo');
    const cargoGroup = document.getElementById('cargo-group');
    const bancaGroup = document.getElementById('banca-group');
    const statsSection = document.getElementById('stats-section');
    const geracaoSection = document.getElementById('geracao-section');

    // Reset
    cargoSelect.innerHTML = '<option value="">-- Escolha um cargo --</option>';
    document.getElementById('stats-list').innerHTML = '';

    if (!orgao) {
        cargoGroup.style.display = 'none';
        bancaGroup.style.display = 'none';
        statsSection.style.display = 'none';
        geracaoSection.style.display = 'none';
        return;
    }

    try {
        const resp = await fetch(`/api/cargos/${orgao}`);
        const data = await resp.json();

        data.cargos.forEach(cargo => {
            const option = document.createElement('option');
            option.value = cargo;
            option.textContent = cargo;
            cargoSelect.appendChild(option);
        });

        cargoGroup.style.display = 'block';
        cargoSelect.addEventListener('change', () => onCargoChange(orgao, cargoSelect.value));
    } catch (erro) {
        console.error('Erro ao carregar cargos:', erro);
    }
}

async function onCargoChange(orgao, cargo) {
    estadoAtual.cargo = cargo;

    const bancaGroup = document.getElementById('banca-group');
    const statsSection = document.getElementById('stats-section');
    const geracaoSection = document.getElementById('geracao-section');

    if (!cargo) {
        bancaGroup.style.display = 'none';
        statsSection.style.display = 'none';
        geracaoSection.style.display = 'none';
        return;
    }

    try {
        // Fetch materias
        const cargoEncoded = encodeURIComponent(cargo);
        const resp = await fetch(`/api/materias/${orgao}/${cargoEncoded}`);
        const data = await resp.json();

        estadoAtual.materias = data.materias;
        estadoAtual.pesos = data.pesos;

        // Fetch stats (coleta atual)
        const statsResp = await fetch(`/api/stats/cargo/${orgao}/${cargoEncoded}`);
        const statsData = await statsResp.json();

        // Display stats
        displayStats(statsData);

        bancaGroup.style.display = 'block';
        statsSection.style.display = 'block';
        geracaoSection.style.display = 'block';

        // Attach button listener
        document.getElementById('btn-gerar').onclick = () => gerarSimulado(orgao, cargo);
    } catch (erro) {
        console.error('Erro ao carregar matérias:', erro);
    }
}

function displayStats(statsData) {
    const title = document.getElementById('stats-title');
    const list = document.getElementById('stats-list');
    const progressText = document.getElementById('progress-text');
    const progressFill = document.getElementById('progress-fill');

    title.textContent = `${statsData.cargo}`;
    list.innerHTML = '';

    const total = statsData.total;
    const percentual = total.percentual || 0;

    progressFill.style.width = `${percentual}%`;
    progressText.textContent = `${total.coletadas}/${total.esperadas} questões (${percentual.toFixed(1)}% completo)`;

    // Display by materia
    Object.entries(statsData.materias).forEach(([materia, stats]) => {
        const div = document.createElement('div');
        div.className = 'materia-item';

        const pct = stats.percentual || 0;
        const statusClass = pct === 0 ? 'status-danger' : pct < 50 ? 'status-warning' : 'status-success';

        div.innerHTML = `
            <h4>${materia}</h4>
            <div class="materia-stats">
                <div class="materia-progress">
                    <div class="materia-progress-fill" style="width: ${pct}%"></div>
                </div>
                <div class="materia-numbers">
                    <span class="${statusClass}">${stats.coletadas}/${stats.esperadas}</span>
                </div>
            </div>
        `;
        list.appendChild(div);
    });
}

async function gerarSimulado(orgao, cargo) {
    const quantidade = parseInt(document.getElementById('quantidade').value) || 60;
    const banca = document.getElementById('banca').value || null;
    const statusDiv = document.getElementById('status-geracao');

    statusDiv.textContent = '⏳ Gerando PDF...';
    statusDiv.className = '';
    statusDiv.style.display = 'block';

    try {
        const body = { quantidade };
        if (banca) body.banca = banca;

        const cargoEncoded = encodeURIComponent(cargo);
        const resp = await fetch(`/api/simulado/cargo/${orgao}/${cargoEncoded}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            throw new Error(`Erro: ${resp.statusText}`);
        }

        const data = await resp.json();
        statusDiv.innerHTML = `
            <p>✓ Simulado gerado com sucesso!</p>
            <a href="/api/simulados/download/${data.arquivo}" class="btn-download">📥 Baixar PDF</a>
        `;
        statusDiv.className = 'success';
    } catch (erro) {
        statusDiv.innerHTML = `<p>❌ Erro: ${erro.message}</p>`;
        statusDiv.className = 'error';
        console.error(erro);
    }
}

async function carregarPainelGeral() {
    try {
        const resp = await fetch('/api/stats/todas');
        const data = await resp.json();

        document.getElementById('total-questoes').textContent = data.total;

        // Matérias
        let htmlMaterias = '<h4>Por Materia:</h4><ul style="columns: 2;">';
        Object.entries(data.por_materia).forEach(([materia, count]) => {
            htmlMaterias += `<li>${materia}: <strong>${count}</strong></li>`;
        });
        htmlMaterias += '</ul>';
        document.getElementById('materias-container').innerHTML = htmlMaterias;

        // Órgãos (top 10)
        let htmlOrgaos = '<h4>Por Orgao (Top 10):</h4><ul>';
        Object.entries(data.por_orgao).slice(0, 10).forEach(([orgao, count]) => {
            htmlOrgaos += `<li>${orgao}: <strong>${count}</strong></li>`;
        });
        htmlOrgaos += '</ul>';
        document.getElementById('orgaos-container').innerHTML = htmlOrgaos;
    } catch (erro) {
        console.error('Erro ao carregar painel:', erro);
    }
}

async function carregarPainelPCI() {
    try {
        const resp = await fetch('/api/stats/pci');
        const data = await resp.json();

        const container = document.getElementById('pci-content');
        let html = `<p style="font-size: 1.2em; font-weight: bold;">Total PCI: ${data.total_pci.toLocaleString()} questoes</p>`;
        html += '<div id="pci-tree" style="margin-top: 20px;"></div>';

        container.innerHTML = html;

        // Renderizar categorias como arvore expansivel
        const tree = document.getElementById('pci-tree');
        for (const [categoria, stats] of Object.entries(data.por_categoria)) {
            const catDiv = document.createElement('div');
            catDiv.className = 'pci-categoria';
            catDiv.innerHTML = `
                <div class="pci-cat-header" onclick="togglePCICat('${categoria}')">
                    <span class="pci-arrow">▶</span>
                    <strong>${categoria}</strong>: ${stats.total} questoes
                </div>
                <div id="pci-${categoria}" class="pci-cat-content" style="display: none; margin-left: 20px;">
                    <div style="color: #999; font-size: 0.9em;">Carregando temas...</div>
                </div>
            `;
            tree.appendChild(catDiv);
        }
    } catch (erro) {
        console.error('Erro ao carregar painel PCI:', erro);
    }
}

async function togglePCICat(categoria) {
    const content = document.getElementById(`pci-${categoria}`);
    const arrow = event.target.closest('.pci-cat-header').querySelector('.pci-arrow');

    if (content.style.display === 'none') {
        // Abrir e carregar temas
        try {
            const resp = await fetch(`/api/stats/pci/${categoria}`);
            const data = await resp.json();

            let html = '';
            for (const [tema, stats] of Object.entries(data.por_tema)) {
                const imgIcon = stats.com_imagens > 0 ? '[img]' : '[-]';
                html += `
                    <div style="padding: 5px 0; border-bottom: 1px solid #eee;">
                        ${imgIcon} <strong>${tema}</strong>: ${stats.total} qs (${stats.percentual_imagens}% com imgs)
                    </div>
                `;
            }
            content.innerHTML = html;
            content.style.display = 'block';
            arrow.textContent = '▼';
        } catch (erro) {
            content.innerHTML = `<p style="color: red;">Erro: ${erro}</p>`;
            content.style.display = 'block';
        }
    } else {
        // Fechar
        content.style.display = 'none';
        arrow.textContent = '▶';
    }
}
