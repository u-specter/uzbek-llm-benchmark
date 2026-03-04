// ═══════════════════════════════════════════════════════════════
// ULAB Dashboard — app.js  (rebuilt)
// ═══════════════════════════════════════════════════════════════

// ── Словари ────────────────────────────────────────────────────
const REG_LABELS = {
  slang:           'Разговорный стиль (слэнг)',
  informal:        'Повседневный стиль',
  formal_business: 'Официальный деловой стиль',
};

const REG_SHORT = {
  slang:           'Разговорный',
  informal:        'Повседневный',
  formal_business: 'Официальный',
};

const DIM_INFO = {
  D1: { name: 'D1 Точность',       tooltip: 'Насколько ответ правильно и полно отвечает на заданный вопрос' },
  D2: { name: 'D2 Язык',           tooltip: 'Грамматика, орфография и правильность узбекского языка' },
  D3: { name: 'D3 Стиль',          tooltip: 'Насколько стиль ответа соответствует требуемому регистру' },
  D4: { name: 'D4 Естественность', tooltip: 'Звучит ли ответ как живой человек, а не машинный перевод' },
};

// Fallback metadata for models not in data.models
const MODEL_FALLBACK = {
  'gemini-flash': { name: 'Gemini 2.0 Flash', provider: 'Google', color: '#4285F4', type: 'commercial' },
  'grok-3':       { name: 'Grok 3',           provider: 'xAI',    color: '#1d9bf0', type: 'commercial' },
};

// grok-2 data is subsumed under grok-3 display (same vendor; hide older if newer present)
const MODEL_SUPERSEDED_BY = { 'grok-2': 'grok-3' };

// ── Состояние ──────────────────────────────────────────────────
const state = {
  activeView:   'lq',

  qaSub:        'all',
  clSub:        'all',
  rbSub:        'all',
  fkSub:        'all',
  rcSub:        'all',
  lqSub:        'all',
  selectedQId:  null,           // selected question id (any module)
  search:       '',
  lbSort:       { col: 'overall', dir: 'desc' },
  lbFilter:     'all',
  lbRanked:     [],
  appData:      null,
};

// ═══════════════════════════════════════════════════════════════
// ИНИЦИАЛИЗАЦИЯ
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  const data = window.BENCHMARK_RESULTS;

  if (!data) {
    document.getElementById('noDataBanner').style.display = 'flex';
    document.getElementById('statusText').textContent = 'Данные не найдены';
    return;
  }

  state.appData = data;
  document.getElementById('app').style.display = 'flex';

  // Header metadata
  const date = data.benchmark_date || '—';
  document.getElementById('benchDate').textContent = `Дата тестирования: ${date}`;
  const modelCount = Object.keys(data.models || {}).length;
  const scored = data.scored_at ? ` · Оценено: ${data.scored_at}` : '';
  document.getElementById('statusText').textContent =
    `${(data.questions || []).length} вопросов · ${modelCount} моделей${scored}`;

  // Question counts in sidebar titles
  const qaCount = (data.questions || []).length;
  const clCount = (data.cl_questions || []).length;
  const rbCount = (data.rb_questions || []).length;
  const fkCount = (data.fk_questions || []).length;
  const rcCount = (data.rc_questions || []).length;
  setTextIfExists('qaTotalCount', qaCount);
  setTextIfExists('clTotalCount', clCount);
  setTextIfExists('rbTotalCount', rbCount);
  setTextIfExists('fkTotalCount', fkCount);
  setTextIfExists('rcTotalCount', rcCount);

  // About page footer note
  const aboutNote = document.getElementById('aboutFooterNote');
  if (aboutNote) {
    aboutNote.textContent = `Дата тестирования: ${data.benchmark_date || '—'} · Оценено: ${data.scored_at || '—'}`;
  }

  setupNavigation();
  setupTooltips();
  renderRatingView();
  renderQAView();
  renderCLView();
  renderRBView();
  renderFKView();
  renderRCView();
  renderLQView();
  renderDeptsView();
});

function setTextIfExists(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ═══════════════════════════════════════════════════════════════
// НАВИГАЦИЯ
// ═══════════════════════════════════════════════════════════════

const VIEW_MAP = {
  rating: 'ratingView',
  qa:     'qaView',
  cl:     'clView',
  rb:     'rbView',
  fk:     'fkView',
  rc:     'rcView',
  lq:     'lqView',
  depts:  'deptsView',
  about:  'aboutView',
};

// Views that use simple block layout (not two-panel flex)
const BLOCK_VIEWS = new Set(['rating', 'about']);

function setupNavigation() {
  document.querySelectorAll('.nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      switchView(btn.dataset.view);
    });
  });
}

function switchView(view) {
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  const tab = document.querySelector(`.nav-tab[data-view="${view}"]`);
  if (tab) tab.classList.add('active');

  Object.values(VIEW_MAP).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  state.activeView = view;
  const targetId = VIEW_MAP[view];
  if (targetId) {
    const el = document.getElementById(targetId);
    if (el) el.style.display = BLOCK_VIEWS.has(view) ? 'block' : 'flex';
  }
}

// ═══════════════════════════════════════════════════════════════
// УТИЛИТЫ
// ═══════════════════════════════════════════════════════════════

function scoreClass(val) {
  if (val == null || val === '') return 'score-red';
  return val >= 80 ? 'score-green' : val >= 60 ? 'score-yellow' : 'score-red';
}

function avgArr(arr) {
  const valid = (arr || []).filter(v => v != null);
  if (!valid.length) return 0;
  return valid.reduce((s, v) => s + v, 0) / valid.length;
}

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function hexToRgba(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(100,100,100,${alpha})`;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function getModelMeta(modelId, data) {
  const d = data || state.appData || {};
  return (d.models || {})[modelId]
    || MODEL_FALLBACK[modelId]
    || { name: modelId, provider: '—', color: '#888', type: 'unknown' };
}

/**
 * Compute itogovy % as simple average of available module scores.
 * Modules: Q&A overall, CL overall, RB overall, FK overall, RC overall.
 */
function computeItogovy(modelId, data) {
  const d = data || state.appData || {};
  const scores = [
    (d.leaderboard      || {})[modelId]?.overall,
    (d.cl_leaderboard   || {})[modelId]?.overall,
    (d.rb_leaderboard   || {})[modelId]?.overall,
    (d.fk_leaderboard   || {})[modelId]?.overall,
    (d.rc_leaderboard   || {})[modelId]?.overall,
    (d.lq_leaderboard   || {})[modelId]?.overall,
  ].filter(v => v != null);
  if (!scores.length) return null;
  return scores.reduce((s, v) => s + v, 0) / scores.length;
}

function scoreBarInline(val, color) {
  if (val == null) return '';
  const pct = Math.min(Math.max(val, 0), 100);
  return `style="background: linear-gradient(to right, ${color || 'rgba(46,124,246,0.15)'} ${pct}%, transparent ${pct}%)"`;
}

function buildSubFilterChips(containerId, options, activeKey, onSelect) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = options.map(opt => `
    <button class="sub-chip ${opt.key === activeKey ? 'active' : ''}"
            data-key="${opt.key}">${escHtml(opt.label)}</button>
  `).join('');
  container.querySelectorAll('.sub-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.sub-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onSelect(btn.dataset.key);
    });
  });
}

// ═══════════════════════════════════════════════════════════════
// СТРАНИЦА РЕЙТИНГА
// ═══════════════════════════════════════════════════════════════

function renderRatingView() {
  const data = state.appData;
  if (!data) return;

  // Build all-model ranked list with itogovy scores
  const allModelsRaw = new Set([
    ...Object.keys(data.models || {}),
    ...Object.keys(data.leaderboard || {}),
    ...Object.keys(data.cl_leaderboard || {}),
    ...Object.keys(data.rb_leaderboard || {}),
    ...Object.keys(data.fk_leaderboard || {}),
    ...Object.keys(data.rc_leaderboard || {}),
    ...Object.keys(data.lq_leaderboard || {}),
  ]);

  // Remove models that are superseded by a newer version of the same model
  const allModels = new Set([...allModelsRaw].filter(id => {
    const newerId = MODEL_SUPERSEDED_BY[id];
    return !(newerId && allModelsRaw.has(newerId));
  }));

  const ranked = [];
  allModels.forEach(id => {
    const overall = computeItogovy(id, data);
    if (overall == null) return;
    ranked.push({
      id,
      overall,
      qa:  (data.leaderboard    || {})[id]?.overall ?? null,
      cl:  (data.cl_leaderboard || {})[id]?.overall ?? null,
      rb:  (data.rb_leaderboard || {})[id]?.overall ?? null,
      fk:  (data.fk_leaderboard || {})[id]?.overall ?? null,
      rc:  (data.rc_leaderboard || {})[id]?.overall ?? null,
      lq:  (data.lq_leaderboard || {})[id]?.overall ?? null,
      meta: getModelMeta(id, data),
    });
  });

  ranked.sort((a, b) => (b.overall || 0) - (a.overall || 0));
  state.lbRanked = ranked;

  renderStatTiles(ranked, data);
  renderLeaderboardTable(ranked);
  setupLbFilter();
  setupLbSort();
}

function renderStatTiles(ranked, data) {
  const container = document.getElementById('statTiles');
  if (!container) return;

  const best = ranked[0];
  const modelCount = ranked.length;
  const qaCount = (data.questions || []).length;

  container.innerHTML = `
    <div class="stat-tile">
      <div class="stat-tile-label">Лучшая модель</div>
      <div class="stat-tile-value">${best ? escHtml(best.meta.name) : '—'}</div>
      ${best ? `<div class="stat-tile-sub ${scoreClass(best.overall)}">${Math.round(best.overall)}%</div>` : ''}
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Протестировано моделей</div>
      <div class="stat-tile-value">${modelCount}</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Всего вопросов</div>
      <div class="stat-tile-value">${qaCount + (data.cl_questions || []).length + (data.rb_questions || []).length + (data.fk_questions || []).length + (data.rc_questions || []).length}</div>
      <div class="stat-tile-sub score-yellow">114 вопросов · 5 модулей</div>
    </div>`;
}

const LB_COLS = [
  { key: 'rank',    label: '#',                sortable: false },
  { key: 'model',   label: 'Модель',           sortable: false },
  { key: 'overall', label: 'Итого',            sortable: true  },
  { key: 'qa',      label: '💬 Генерация',     sortable: true  },
  { key: 'cl',      label: '🏷 Классиф.',      sortable: true  },
  { key: 'rb',      label: '🔤 Устойчивость',  sortable: true  },
  { key: 'fk',      label: '✅ Факты',         sortable: true  },
  { key: 'rc',      label: '📖 Понимание',     sortable: true  },
  { key: 'lq',      label: '⚖️ Юрид. Q&A',    sortable: true  },
];

function renderLeaderboardTable(ranked) {
  const sort  = state.lbSort;
  const medals = ['🥇', '🥈', '🥉'];

  // Sort
  let sorted = [...ranked];
  if (sort.col !== 'overall' || sort.dir !== 'desc') {
    sorted.sort((a, b) => {
      const av = a[sort.col] ?? -1;
      const bv = b[sort.col] ?? -1;
      return sort.dir === 'desc' ? bv - av : av - bv;
    });
  }

  const thead = LB_COLS.map(col => {
    if (!col.sortable) return `<th>${col.label}</th>`;
    const isActive = sort.col === col.key;
    const arrow = isActive ? (sort.dir === 'desc' ? ' ↓' : ' ↑') : '';
    return `<th class="th-sortable th-center ${isActive ? 'th-active' : ''}"
                data-sort="${col.key}" style="cursor:pointer">${col.label}${arrow}</th>`;
  }).join('');

  const rows = sorted.map((m, i) => {
    const rankCell = i < 3
      ? `<span class="rank-medal">${medals[i]}</span>`
      : `<span class="rank-num">#${i + 1}</span>`;

    const scoreCell = (val) => {
      if (val == null) return `<td class="td-mod" style="text-align:center"><span class="na-text">—</span></td>`;
      const cls  = scoreClass(val);
      const pct  = Math.min(Math.max(val, 0), 100);
      return `<td class="td-mod score-cell-inline" style="text-align:center">
        <span class="score-inline-val ${cls}"
              ${scoreBarInline(val, 'rgba(46,124,246,0.12)')}>${Math.round(val)}</span>
      </td>`;
    };

    const bg = i === 0 ? 'rgba(245,158,11,0.05)'
             : i === 1 ? 'rgba(148,163,184,0.05)'
             : i === 2 ? 'rgba(180,83,9,0.05)' : '';

    return `
      <tr${bg ? ` style="background:${bg}"` : ''}>
        <td class="td-rank">${rankCell}</td>
        <td class="td-model">
          <div class="model-cell model-cell-clickable"
               onclick="openModelDrawer('${m.id}')"
               title="Подробная карточка модели">
            <div class="model-dot" style="background:${m.meta.color}"></div>
            <div>
              <div class="model-name">${escHtml(m.meta.name)}</div>
              <div class="model-sub">
                ${escHtml(m.meta.provider || '')}
                <span class="type-badge type-${m.meta.type}">
                  ${m.meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
                </span>
              </div>
            </div>
            <span class="model-arrow">›</span>
          </div>
        </td>
        ${scoreCell(m.overall)}
        ${scoreCell(m.qa)}
        ${scoreCell(m.cl)}
        ${scoreCell(m.rb)}
        ${scoreCell(m.fk)}
        ${scoreCell(m.rc)}
      </tr>`;
  }).join('');

  document.getElementById('lbTable').innerHTML = `
    <thead><tr>${thead}</tr></thead>
    <tbody>${rows}</tbody>`;
}

function setupLbFilter() {
  document.querySelectorAll('.lb-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.lb-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.lbFilter = btn.dataset.filter;
      applyLbFilter();
    });
  });
}

function applyLbFilter() {
  let filtered = state.lbRanked;
  if (state.lbFilter === 'commercial') {
    filtered = state.lbRanked.filter(m => m.meta.type === 'commercial');
  } else if (state.lbFilter === 'opensource') {
    filtered = state.lbRanked.filter(m => m.meta.type !== 'commercial');
  }
  renderLeaderboardTable(filtered);
}

function setupLbSort() {
  // Use event delegation on the table
  const table = document.getElementById('lbTable');
  if (!table) return;
  table.addEventListener('click', e => {
    const th = e.target.closest('[data-sort]');
    if (!th) return;
    const col = th.dataset.sort;
    if (state.lbSort.col === col) {
      state.lbSort.dir = state.lbSort.dir === 'desc' ? 'asc' : 'desc';
    } else {
      state.lbSort.col = col;
      state.lbSort.dir = 'desc';
    }
    applyLbFilter();
  });
}

// ═══════════════════════════════════════════════════════════════
// MODEL DRAWER + RADAR CHART
// ═══════════════════════════════════════════════════════════════

function openModelDrawer(modelId) {
  const data = state.appData;
  if (!data) return;

  const meta    = getModelMeta(modelId, data);
  const qaScore = (data.leaderboard    || {})[modelId]?.overall ?? null;
  const clScore = (data.cl_leaderboard || {})[modelId]?.overall ?? null;
  const rbScore = (data.rb_leaderboard || {})[modelId]?.overall ?? null;
  const fkScore = (data.fk_leaderboard || {})[modelId]?.overall ?? null;
  const rcScore = (data.rc_leaderboard || {})[modelId]?.overall ?? null;

  const itogovy = computeItogovy(modelId, data);

  // 5-axis radar: Q&A, CL, RB, FK, RC
  const radarLabels = ['Q&A', 'CL', 'RB', 'FK', 'RC'];
  const radarValues = [qaScore, clScore, rbScore, fkScore, rcScore];

  // Module breakdown rows
  const modules = [
    { label: 'Q&A (генерация)',           val: qaScore },
    { label: 'CL (классификация)',         val: clScore },
    { label: 'RB (устойчивость к шуму)',   val: rbScore },
    { label: 'FK (проверка фактов)',        val: fkScore },
    { label: 'RC (понимание текста)',       val: rcScore },
  ].filter(r => r.val != null);

  // Auto-insight: best/worst module
  const sorted = [...modules].sort((a, b) => (b.val || 0) - (a.val || 0));
  const insightHtml = sorted.length >= 2
    ? `<div class="drawer-insight">Лучший результат: <strong>${sorted[0].label.split('(')[0].trim()}</strong>. Наихудший: <strong>${sorted[sorted.length - 1].label.split('(')[0].trim()}</strong>.</div>`
    : '';

  document.getElementById('drawerContent').innerHTML = `
    <div class="drawer-model-header" style="border-left:4px solid ${meta.color}">
      <div class="drawer-model-dot" style="background:${meta.color}"></div>
      <div>
        <div class="drawer-model-name">${escHtml(meta.name)}</div>
        <div class="drawer-model-sub">
          ${escHtml(meta.provider || '')}
          <span class="type-badge type-${meta.type}" style="margin-left:6px">
            ${meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
          </span>
          ${itogovy != null ? `<span class="drawer-itogovy ${scoreClass(itogovy)}">Итог: ${Math.round(itogovy)}%</span>` : ''}
        </div>
      </div>
    </div>

    <div class="drawer-radar-wrap">
      <canvas id="radarChart" width="300" height="300"></canvas>
    </div>

    <div class="drawer-scores">
      <div class="drawer-scores-title">Детализация по модулям</div>
      ${modules.map(r => `
        <div class="drawer-score-row">
          <span class="drawer-score-label">${r.label}</span>
          <div class="drawer-score-bar-wrap">
            <div class="drawer-score-bar" style="width:${Math.min(r.val, 100)}%;background:${meta.color}"></div>
          </div>
          <span class="drawer-score-val ${scoreClass(r.val)}">${Math.round(r.val)}</span>
        </div>`).join('')}
    </div>

    ${insightHtml}`;

  document.getElementById('modelDrawerOverlay').style.display = 'block';
  document.getElementById('modelDrawer').style.display        = 'flex';
  document.body.style.overflow = 'hidden';

  requestAnimationFrame(() => drawRadar(radarLabels, radarValues, meta.color));
}

function closeModelDrawer() {
  document.getElementById('modelDrawerOverlay').style.display = 'none';
  document.getElementById('modelDrawer').style.display        = 'none';
  document.body.style.overflow = '';
  if (window._radarChart) { window._radarChart.destroy(); window._radarChart = null; }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModelDrawer();
});

function drawRadar(labels, values, color) {
  const ctx = document.getElementById('radarChart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (window._radarChart) { window._radarChart.destroy(); window._radarChart = null; }

  const displayValues = values.map(v => v ?? 0);
  const rgba = hexToRgba(color, 0.18);

  window._radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Баллы',
        data: displayValues,
        backgroundColor: rgba,
        borderColor: color,
        borderWidth: 2.5,
        pointBackgroundColor: displayValues.map((v, i) =>
          values[i] == null ? 'rgba(0,0,0,0.15)' : color
        ),
        pointRadius: 4,
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: false,
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { stepSize: 25, font: { size: 9 }, backdropColor: 'transparent', color: '#64748B' },
          pointLabels: { font: { size: 11, weight: '500' }, color: '#1A1A2E' },
          grid: { color: 'rgba(0,0,0,0.07)' },
          angleLines: { color: 'rgba(0,0,0,0.08)' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${Math.round(ctx.raw)} / 100` } },
      },
      animation: { duration: 500, easing: 'easeOutQuart' },
    },
  });
}

// ═══════════════════════════════════════════════════════════════
// TOOLTIPS
// ═══════════════════════════════════════════════════════════════

function setupTooltips() {
  const tip = document.getElementById('tooltip');

  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-tooltip]');
    if (!el) return;
    tip.textContent = el.dataset.tooltip;
    tip.style.display = 'block';
  });

  document.addEventListener('mouseout', e => {
    if (!e.target.closest('[data-tooltip]')) return;
    tip.style.display = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (tip.style.display === 'none') return;
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY - 10) + 'px';
  });
}

// ═══════════════════════════════════════════════════════════════
// Q&A PAGE
// ═══════════════════════════════════════════════════════════════

function renderQAView() {
  const data = state.appData;
  if (!data || !data.questions) return;

  const qaSubOptions = [
    { key: 'all',             label: 'Все' },
    { key: 'formal_business', label: 'Официальный' },
    { key: 'informal',        label: 'Повседневный' },
    { key: 'slang',           label: 'Разговорный' },
  ];

  buildSubFilterChips('qaSubFilter', qaSubOptions, state.qaSub, (key) => {
    state.qaSub = key;
    state.selectedQId = null;
    renderQAList();
    resetQAContent();
  });

  document.getElementById('qaSearchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderQAList();
  });

  renderQAList();
}

function getFilteredQAQuestions() {
  const data = state.appData;
  let qs = data.questions || [];
  if (state.qaSub !== 'all') qs = qs.filter(q => q.register === state.qaSub);
  if (state.search) {
    qs = qs.filter(q =>
      (q.text || '').toLowerCase().includes(state.search) ||
      (q.id || '').toLowerCase().includes(state.search)
    );
  }
  return qs;
}

function renderQAList() {
  const qs = getFilteredQAQuestions();
  const list = document.getElementById('qaList');
  if (!list) return;

  if (!qs.length) {
    list.innerHTML = '<div class="q-empty">Ничего не найдено.</div>';
    return;
  }

  list.innerHTML = qs.map(q => {
    const responses = q.responses || {};
    const scores = Object.values(responses).map(r => r.scores?.total).filter(t => t != null);
    const best  = scores.length ? Math.round(Math.max(...scores)) : null;
    const worst = scores.length ? Math.round(Math.min(...scores)) : null;

    return `
      <div class="q-item ${q.id === state.selectedQId ? 'active' : ''}" data-id="${q.id}"
           onclick="selectQAQuestion('${q.id}')">
        <div class="q-item-top">
          <span class="q-item-num">${q.id}</span>
          <span class="q-item-reg badge-${q.register}">${REG_SHORT[q.register] || q.register}</span>
        </div>
        <div class="q-item-text">${escHtml(q.text)}</div>
        ${best != null ? `<div class="q-item-stats">Лучший: ${best} · Худший: ${worst}</div>` : ''}
      </div>`;
  }).join('');
}

function resetQAContent() {
  const content = document.getElementById('qaContent');
  if (content) content.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">←</div>
      <p>Выберите вопрос из списка слева</p>
    </div>`;
}

// QA sort state
const qaSort = { by: 'score' };

function selectQAQuestion(qId) {
  const data = state.appData;
  state.selectedQId = qId;
  qaSort.by = 'score';

  document.querySelectorAll('#qaList .q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );

  const q = (data.questions || []).find(x => x.id === qId);
  if (!q) return;

  const content = document.getElementById('qaContent');

  content.innerHTML = `
    <div class="q-detail">
      <div class="q-detail-header">
        <div class="q-detail-meta">
          <span class="q-detail-id">${q.id}</span>
          <span class="q-detail-reg badge-${q.register}">${REG_LABELS[q.register] || q.register}</span>
        </div>
        <div class="q-detail-question">${escHtml(q.text)}</div>
      </div>

      <div class="qa-sort-bar">
        <span class="qa-sort-label">Сортировка:</span>
        <button class="qa-sort-btn active" data-by="score">По баллу ↓</button>
        <button class="qa-sort-btn" data-by="D1">D1</button>
        <button class="qa-sort-btn" data-by="D2">D2</button>
        <button class="qa-sort-btn" data-by="D3">D3</button>
        <button class="qa-sort-btn" data-by="D4">D4</button>
      </div>

      <div id="qaRespArea" class="qa-resp-area"></div>
    </div>`;

  // Sort bar handlers
  content.querySelectorAll('.qa-sort-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      content.querySelectorAll('.qa-sort-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      qaSort.by = btn.dataset.by;
      renderQARespCards(q);
    });
  });

  renderQARespCards(q);
}

function renderQARespCards(q) {
  const data = state.appData;
  const area = document.getElementById('qaRespArea');
  if (!area) return;

  const responses = q.responses || {};
  let entries = Object.entries(responses);

  // Sort by selected criterion
  entries.sort(([, a], [, b]) => {
    let av, bv;
    if (qaSort.by === 'score') {
      av = a.scores?.total ?? -1;
      bv = b.scores?.total ?? -1;
    } else {
      av = a.scores?.[qaSort.by] ?? -1;
      bv = b.scores?.[qaSort.by] ?? -1;
    }
    return bv - av;
  });

  const allScores = entries.map(([, r]) => r.scores?.total).filter(t => t != null);
  const maxScore  = allScores.length ? Math.max(...allScores) : null;
  const minScore  = allScores.length ? Math.min(...allScores) : null;

  area.innerHTML = entries.map(([modelId, resp]) => {
    const meta   = getModelMeta(modelId, data);
    const scores = resp.scores || {};
    const total  = scores.total;

    let cardCls = 'resp-card';
    if (total != null && maxScore != null && minScore != null && maxScore !== minScore) {
      if (total === maxScore) cardCls += ' resp-card-best';
      else if (total === minScore) cardCls += ' resp-card-worst';
    }

    const dimRows = ['D1', 'D2', 'D3', 'D4'].map(d => {
      const val = scores[d];
      if (val == null) return '';
      return `
        <div class="qa-dim-row">
          <span class="qa-dim-label" data-tooltip="${escHtml(DIM_INFO[d].tooltip)}">${DIM_INFO[d].name}</span>
          <div class="qa-dim-bar-wrap">
            <div class="qa-dim-bar" style="width:${Math.round(val / 5 * 100)}%;background:${meta.color}"></div>
          </div>
          <span class="qa-dim-val ${scoreClass(val / 5 * 100)}">${val}</span>
        </div>`;
    }).join('');

    const text   = resp.response || '';
    const isLong = text.length > 400;

    return `
      <div class="${cardCls}">
        <div class="resp-header">
          <div class="resp-header-row">
            <div class="resp-model-info">
              <div class="resp-model-dot" style="background:${meta.color}"></div>
              <div>
                <div class="resp-model-name" style="cursor:pointer" onclick="openModelDrawer('${modelId}')">${escHtml(meta.name)}</div>
                <div class="resp-model-sub">${escHtml(meta.provider || '')}</div>
              </div>
            </div>
            ${total != null ? `<div class="resp-score-box">
              <div class="resp-score-num ${scoreClass(total)}">${Math.round(total)}</div>
              <div class="resp-score-sub">Итог</div>
            </div>` : ''}
          </div>
        </div>
        <div class="resp-body">
          ${dimRows ? `<div class="qa-dims">${dimRows}</div>` : ''}
          <div class="resp-text ${isLong ? '' : ''}">${escHtml(text)}</div>
          ${isLong ? `<button class="expand-btn" onclick="toggleExpandText(this)">Развернуть ▼</button>` : ''}
        </div>
      </div>`;
  }).join('');
}

function toggleExpandText(btn) {
  const textEl = btn.previousElementSibling;
  const expanded = textEl.classList.toggle('expanded');
  btn.textContent = expanded ? 'Свернуть ▲' : 'Развернуть ▼';
}

// ═══════════════════════════════════════════════════════════════
// CL PAGE
// ═══════════════════════════════════════════════════════════════

function renderCLView() {
  const data = state.appData;
  if (!data || !data.cl_questions) return;

  const clSubOptions = [
    { key: 'all',       label: 'Все' },
    { key: 'sentiment', label: 'Тональность' },
    { key: 'intent',    label: 'Намерение' },
    { key: 'register',  label: 'Стиль речи' },
  ];

  buildSubFilterChips('clSubFilter', clSubOptions, state.clSub, (key) => {
    state.clSub = key;
    state.selectedQId = null;
    renderCLList();
    resetContent('clContent');
  });

  document.getElementById('clSearchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderCLList();
  });

  renderCLList();
}

function getFilteredCLQuestions() {
  const data = state.appData;
  let qs = data.cl_questions || [];
  if (state.clSub !== 'all') qs = qs.filter(q => q.type === state.clSub);
  if (state.search) {
    qs = qs.filter(q =>
      (q.text || '').toLowerCase().includes(state.search) ||
      (q.id || '').toLowerCase().includes(state.search)
    );
  }
  return qs;
}

function renderCLList() {
  const qs = getFilteredCLQuestions();
  renderBinaryList('clList', qs, 'cl', state.selectedQId, selectCLQuestion);
}

function selectCLQuestion(qId) {
  state.selectedQId = qId;
  document.querySelectorAll('#clList .q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );
  const q = (state.appData.cl_questions || []).find(x => x.id === qId);
  if (!q) return;
  renderBinaryDetail('clContent', q, 'Классификация');
}

// ═══════════════════════════════════════════════════════════════
// RB / FK / RC PAGES
// ═══════════════════════════════════════════════════════════════

// ── RB ──
function renderRBView() {
  const data = state.appData;
  if (!data || !data.rb_questions) return;

  const rbSubOptions = [
    { key: 'all',             label: 'Все' },
    { key: 'apostrophe_drop', label: 'Пропущен апостроф' },
    { key: 'typo',            label: 'Опечатки' },
    { key: 'cyrillic_mix',    label: 'Кириллица в латинском' },
  ];

  buildSubFilterChips('rbSubFilter', rbSubOptions, state.rbSub, (key) => {
    state.rbSub = key;
    state.selectedQId = null;
    renderRBList();
    resetContent('rbContent');
  });

  document.getElementById('rbSearchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderRBList();
  });

  renderRBList();
}

function getFilteredRBQuestions() {
  const data = state.appData;
  let qs = data.rb_questions || [];
  if (state.rbSub !== 'all') qs = qs.filter(q => q.type === state.rbSub);
  if (state.search) {
    qs = qs.filter(q =>
      (q.text || '').toLowerCase().includes(state.search) ||
      (q.id || '').toLowerCase().includes(state.search)
    );
  }
  return qs;
}

function renderRBList() {
  const qs = getFilteredRBQuestions();
  renderBinaryList('rbList', qs, 'rb', state.selectedQId, selectRBQuestion);
}

function selectRBQuestion(qId) {
  state.selectedQId = qId;
  document.querySelectorAll('#rbList .q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );
  const q = (state.appData.rb_questions || []).find(x => x.id === qId);
  if (!q) return;
  renderBinaryDetail('rbContent', q, 'Устойчивость к шуму');
}

// ── FK ──
function renderFKView() {
  const data = state.appData;
  if (!data || !data.fk_questions) return;

  const fkSubOptions = [
    { key: 'all',      label: 'Все' },
    { key: 'country',  label: 'О стране' },
    { key: 'currency', label: 'О валюте' },
    { key: 'banking',  label: 'О банках' },
  ];

  buildSubFilterChips('fkSubFilter', fkSubOptions, state.fkSub, (key) => {
    state.fkSub = key;
    state.selectedQId = null;
    renderFKList();
    resetContent('fkContent');
  });

  document.getElementById('fkSearchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderFKList();
  });

  renderFKList();
}

function getFilteredFKQuestions() {
  const data = state.appData;
  let qs = data.fk_questions || [];
  if (state.fkSub !== 'all') qs = qs.filter(q => q.type === state.fkSub);
  if (state.search) {
    qs = qs.filter(q =>
      (q.text || '').toLowerCase().includes(state.search) ||
      (q.id || '').toLowerCase().includes(state.search)
    );
  }
  return qs;
}

function renderFKList() {
  const qs = getFilteredFKQuestions();
  renderBinaryList('fkList', qs, 'fk', state.selectedQId, selectFKQuestion);
}

function selectFKQuestion(qId) {
  state.selectedQId = qId;
  document.querySelectorAll('#fkList .q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );
  const q = (state.appData.fk_questions || []).find(x => x.id === qId);
  if (!q) return;
  renderBinaryDetail('fkContent', q, 'Проверка фактов');
}

// ── RC ──
function renderRCView() {
  const data = state.appData;
  if (!data || !data.rc_questions) return;

  const rcSubOptions = [
    { key: 'all',           label: 'Все' },
    { key: 'kredit_freeze', label: 'Заморозка кредитов' },
    { key: 'pul_otkazma',   label: 'Денежные переводы' },
  ];

  buildSubFilterChips('rcSubFilter', rcSubOptions, state.rcSub, (key) => {
    state.rcSub = key;
    state.selectedQId = null;
    renderRCList();
    resetContent('rcContent');
  });

  document.getElementById('rcSearchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderRCList();
  });

  renderRCList();
}

function getFilteredRCQuestions() {
  const data = state.appData;
  let qs = (data.rc_questions || []).filter(q => q.type !== 'hayot_bank');
  if (state.rcSub !== 'all') qs = qs.filter(q => q.type === state.rcSub);
  if (state.search) {
    qs = qs.filter(q =>
      (q.question || q.text || '').toLowerCase().includes(state.search) ||
      (q.id || '').toLowerCase().includes(state.search)
    );
  }
  return qs;
}

function renderRCList() {
  const qs = getFilteredRCQuestions();
  const list = document.getElementById('rcList');
  if (!list) return;

  if (!qs.length) {
    list.innerHTML = '<div class="q-empty">Ничего не найдено.</div>';
    return;
  }

  list.innerHTML = qs.map(q => {
    const responses = q.responses || {};
    const total = Object.keys(responses).length;
    const correct = Object.values(responses).filter(r => r.correct).length;

    return `
      <div class="q-item ${q.id === state.selectedQId ? 'active' : ''}" data-id="${q.id}"
           onclick="selectRCQuestion('${q.id}')">
        <div class="q-item-top">
          <span class="q-item-num">${q.id}</span>
          <span class="q-item-reg badge-informal">${q.type || 'rc'}</span>
        </div>
        <div class="q-item-text">${escHtml(q.question || q.text || '')}</div>
        <div class="q-item-stats">Правильно: ${correct}/${total}</div>
      </div>`;
  }).join('');
}

function selectRCQuestion(qId) {
  state.selectedQId = qId;
  document.querySelectorAll('#rcList .q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );
  const q = (state.appData.rc_questions || []).find(x => x.id === qId);
  if (!q) return;
  renderRCDetail(q);
}

// ═══════════════════════════════════════════════════════════════
// BINARY LIST RENDERER (shared for CL / RB)
// ═══════════════════════════════════════════════════════════════

// Map module → global select function name (used in inline onclick)
const BINARY_SELECT_FN = { cl: 'selectCLQuestion', rb: 'selectRBQuestion', fk: 'selectFKQuestion' };

function renderBinaryList(listId, qs, module, selectedId, onSelect) {
  const list = document.getElementById(listId);
  if (!list) return;

  if (!qs.length) {
    list.innerHTML = '<div class="q-empty">Ничего не найдено.</div>';
    return;
  }

  const selectFn = BINARY_SELECT_FN[module] || 'selectRBQuestion';

  list.innerHTML = qs.map(q => {
    const responses = q.responses || {};
    const total   = Object.keys(responses).length;
    const correct = Object.values(responses).filter(r => r.correct).length;

    return `
      <div class="q-item ${q.id === selectedId ? 'active' : ''}" data-id="${q.id}"
           onclick="${selectFn}('${q.id}')">
        <div class="q-item-top">
          <span class="q-item-num">${q.id}</span>
          <span class="q-item-reg badge-formal_business">${q.type || module}</span>
        </div>
        <div class="q-item-text">${escHtml(q.text || '')}</div>
        <div class="q-item-stats">Правильно: ${correct}/${total}</div>
      </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════
// BINARY DETAIL RENDERER (shared for CL / RB / FK)
// ═══════════════════════════════════════════════════════════════

function renderBinaryDetail(contentId, q, moduleLabel) {
  const data = state.appData;
  const content = document.getElementById(contentId);
  if (!content) return;

  const responses = q.responses || {};
  const total     = Object.keys(responses).length;
  const correct   = Object.values(responses).filter(r => r.correct).length;

  // Sort: correct first, then wrong
  const entries = Object.entries(responses).sort(([, a], [, b]) => {
    return (b.correct ? 1 : 0) - (a.correct ? 1 : 0);
  });

  const cards = entries.map(([modelId, resp]) => {
    const meta   = getModelMeta(modelId, data);
    const isCorr = resp.correct;
    return `
      <div class="binary-card ${isCorr ? 'correct' : 'wrong'}">
        <div class="binary-card-header">
          <span class="binary-model-name" onclick="openModelDrawer('${modelId}')" style="cursor:pointer">
            ${escHtml(meta.name)}
          </span>
          <span class="binary-result ${isCorr ? 'score-green' : 'score-red'}">
            ${isCorr ? '✓ Правильно' : '✗ Неправильно'}
          </span>
        </div>
        <div class="binary-answers">
          <div>Ответ модели: <strong>${escHtml(String(resp.parsed ?? resp.response ?? ''))}</strong></div>
          <div>Правильный: <strong>${escHtml(String(q.answer ?? ''))}</strong></div>
        </div>
      </div>`;
  }).join('');

  content.innerHTML = `
    <div class="q-detail">
      <div class="q-detail-header">
        <div class="q-detail-meta">
          <span class="q-detail-id">${q.id}</span>
          <span class="q-detail-reg badge-formal_business">${moduleLabel} · ${q.type || ''}</span>
        </div>
        <div class="q-detail-question">${escHtml(q.text || '')}</div>
        <div class="q-detail-note">
          Правильный ответ: <strong>${escHtml(String(q.answer ?? ''))}</strong>
          &nbsp;·&nbsp; Правильно ответили: <strong>${correct} из ${total}</strong>
        </div>
      </div>
      <div class="binary-cards-grid">${cards}</div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════════
// RC DETAIL RENDERER
// ═══════════════════════════════════════════════════════════════

function renderRCDetail(q) {
  const data = state.appData;
  const content = document.getElementById('rcContent');
  if (!content) return;

  const responses = q.responses || {};
  const total     = Object.keys(responses).length;
  const correct   = Object.values(responses).filter(r => r.correct).length;

  // Answer choices A/B/C/D
  // q.choices may be an object {A: "...", B: "..."} or an array
  const correctAnswer = q.answer || '';
  const rawChoices = q.choices || {};
  const choiceEntries = Array.isArray(rawChoices)
    ? rawChoices.map((text, i) => [['A','B','C','D'][i] || String(i+1), text])
    : Object.entries(rawChoices);

  const choicesHtml = choiceEntries.map(([letter, text]) => {
    const isCorrect = letter === correctAnswer;
    return `
      <div class="choice-item ${isCorrect ? 'choice-correct' : ''}">
        <span class="choice-letter">${letter}.</span>
        <span class="choice-text">${escHtml(text)}</span>
        ${isCorrect ? '<span class="choice-mark">← Правильный ✓</span>' : ''}
      </div>`;
  }).join('');

  // Sort: correct first
  const entries = Object.entries(responses).sort(([, a], [, b]) =>
    (b.correct ? 1 : 0) - (a.correct ? 1 : 0)
  );

  const cards = entries.map(([modelId, resp]) => {
    const meta   = getModelMeta(modelId, data);
    const isCorr = resp.correct;
    return `
      <div class="binary-card ${isCorr ? 'correct' : 'wrong'}">
        <div class="binary-card-header">
          <span class="binary-model-name" onclick="openModelDrawer('${modelId}')" style="cursor:pointer">
            ${escHtml(meta.name)}
          </span>
          <span class="binary-result ${isCorr ? 'score-green' : 'score-red'}">
            ${isCorr ? '✓' : '✗'} ${escHtml(String(resp.parsed ?? resp.response ?? ''))} / ${escHtml(correctAnswer)}
          </span>
        </div>
      </div>`;
  }).join('');

  const passage = q.passage || '';

  content.innerHTML = `
    <div class="q-detail">
      <div class="q-detail-header">
        <div class="q-detail-meta">
          <span class="q-detail-id">${q.id}</span>
          <span class="q-detail-reg badge-informal">RC · ${q.type || ''}</span>
        </div>

        <div class="rc-passage-wrap">
          <div class="rc-passage-label">Отрывок:</div>
          <div class="rc-passage collapsed" id="rcPassage_${q.id}">${escHtml(passage)}</div>
          ${passage.length > 300
            ? `<button class="rc-passage-toggle" onclick="toggleRCPassage('${q.id}', this)">Показать полностью</button>`
            : ''
          }
        </div>

        <div class="q-detail-question" style="margin-top:16px">
          <strong>Вопрос:</strong> ${escHtml(q.question || '')}
        </div>

        <div class="choices-list">${choicesHtml}</div>

        <div class="q-detail-note">Правильно ответили: <strong>${correct} из ${total}</strong></div>
      </div>

      <div class="binary-cards-grid">${cards}</div>
    </div>`;
}

function toggleRCPassage(qId, btn) {
  const el = document.getElementById(`rcPassage_${qId}`);
  if (!el) return;
  const collapsed = el.classList.toggle('collapsed');
  btn.textContent = collapsed ? 'Показать полностью' : 'Свернуть';
}

// ═══════════════════════════════════════════════════════════════
// LQ — Legal Q&A (wakilai-legal-benchmark-uz, 60 questions)
// ═══════════════════════════════════════════════════════════════

const LQ_TYPE_LABELS = {
  moliya:      'Солиқ ва молия',
  biznes:      'Тадбиркорлик',
  raqamli:     'Давлат хизматлари',
  istemolchi:  'Истеъмолчилар',
  sugurta:     'Суғурта',
  audit:       'Аудит',
  valyuta:     'Божхона / Валюта',
  lombard:     'Ломбард',
};

function renderLQView() {
  const data = state.appData;
  const qs   = (data.lq_questions || []);

  document.getElementById('lqTotalCount').textContent = qs.length;

  const types = [...new Set(qs.map(q => q.type))].filter(Boolean);
  const lqSubOptions = types.map(t => ({ key: t, label: LQ_TYPE_LABELS[t] || t }));

  buildSubFilterChips('lqSubFilter', lqSubOptions, state.lqSub, (key) => {
    state.lqSub = key;
    renderLQList();
    resetContent('lqContent');
  });

  document.getElementById('lqSearchInput').addEventListener('input', () => {
    renderLQList();
    resetContent('lqContent');
  });

  renderLQList();
}

function getFilteredLQQuestions() {
  const data   = state.appData;
  const search = (document.getElementById('lqSearchInput')?.value || '').toLowerCase();
  let qs = (data.lq_questions || []);
  if (state.lqSub) qs = qs.filter(q => q.type === state.lqSub);
  if (search) qs = qs.filter(q =>
    (q.question || '').toLowerCase().includes(search) ||
    (q.reference_answer || '').toLowerCase().includes(search)
  );
  return qs;
}

function renderLQList() {
  const qs      = getFilteredLQQuestions();
  const listEl  = document.getElementById('lqList');
  if (!listEl) return;

  if (!qs.length) {
    listEl.innerHTML = '<div class="q-list-empty">Вопросы не найдены</div>';
    return;
  }

  listEl.innerHTML = qs.map(q => {
    const responses = q.responses || {};
    const total   = Object.keys(responses).length;
    const avgScore = total
      ? Math.round(Object.values(responses).reduce((s, r) => s + (r.score || 0), 0) / total)
      : null;
    const typeLabel = LQ_TYPE_LABELS[q.type] || q.type || '';
    return `
      <div class="q-item" onclick="selectLQQuestion('${q.id}')">
        <div class="q-item-header">
          <span class="q-id">${q.id}</span>
          <span class="q-reg badge-formal">${escHtml(typeLabel)}</span>
          ${avgScore != null ? `<span class="q-score ${scoreClass(avgScore)}">${avgScore}%</span>` : ''}
        </div>
        <div class="q-preview">${escHtml((q.question || '').slice(0, 90))}</div>
      </div>`;
  }).join('');
}

function selectLQQuestion(qId) {
  const data = state.appData;
  const q    = (data.lq_questions || []).find(x => x.id === qId);
  if (!q) return;

  document.querySelectorAll('#lqList .q-item').forEach(el => el.classList.remove('active'));
  const activeEl = [...document.querySelectorAll('#lqList .q-item')]
    .find(el => el.querySelector('.q-id')?.textContent === qId);
  if (activeEl) activeEl.classList.add('active');

  renderLQDetail(q);
}

function renderLQDetail(q) {
  const data    = state.appData;
  const content = document.getElementById('lqContent');
  if (!content) return;

  const responses = q.responses || {};
  const entries   = Object.entries(responses).sort(([, a], [, b]) => (b.score || 0) - (a.score || 0));

  const scoreIcon = s => s === 100 ? '✓' : (s === 50 ? '~' : '✗');
  const scoreLabel = s => s === 100 ? "to'g'ri" : (s === 50 ? 'qisman' : "noto'g'ri");

  const cards = entries.map(([modelId, resp]) => {
    const meta  = getModelMeta(modelId, data);
    const score = resp.score ?? 0;
    const cls   = score === 100 ? 'correct' : (score === 50 ? 'partial' : 'wrong');
    return `
      <div class="binary-card ${cls}">
        <div class="binary-card-header">
          <span class="binary-model-name" onclick="openModelDrawer('${modelId}')" style="cursor:pointer">
            ${escHtml(meta.name)}
          </span>
          <span class="binary-result ${score === 100 ? 'score-green' : score === 50 ? 'score-yellow' : 'score-red'}">
            ${scoreIcon(score)} ${scoreLabel(score)} · ${score}
          </span>
        </div>
        <div class="lq-model-answer">${escHtml(resp.response || '')}</div>
      </div>`;
  }).join('');

  content.innerHTML = `
    <div class="q-detail">
      <div class="q-detail-header">
        <div class="q-detail-meta">
          <span class="q-detail-id">${q.id}</span>
          <span class="q-detail-reg badge-formal">⚖️ ${escHtml(LQ_TYPE_LABELS[q.type] || q.type || '')}</span>
        </div>

        <div class="q-detail-question" style="margin-bottom:12px">
          <strong>Savol:</strong> ${escHtml(q.question || '')}
        </div>

        <div class="lq-reference-wrap">
          <div class="lq-reference-label">📌 Эталонный ответ:</div>
          <div class="lq-reference-text">${escHtml(q.reference_answer || '')}</div>
          <div class="lq-source">Источник: wakilai-legal-benchmark-uz</div>
        </div>

        <div class="q-detail-note">Протестировано моделей: <strong>${entries.length}</strong></div>
      </div>

      <div class="binary-cards-grid">${cards || '<p style="color:var(--muted);padding:20px">Ответы ещё не собраны. Запустите run_benchmark_lq.py</p>'}</div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════

function resetContent(contentId) {
  const el = document.getElementById(contentId);
  if (el) el.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">←</div>
      <p>Выберите вопрос из списка слева</p>
    </div>`;
}

// ═══════════════════════════════════════════════════════════════
// ДЕПАРТАМЕНТЫ — РЕКОМЕНДАЦИИ МОДЕЛЕЙ
// ═══════════════════════════════════════════════════════════════

// Каждый департамент: id, icon, name, desc, weights по суб-метрикам, strengths
const DEPARTMENTS = [
  {
    id: 'callcenter',
    icon: '📞',
    name: 'Колл-центр',
    desc: 'Операторы отвечают на звонки и чаты клиентов. ИИ должен понимать неформальные сообщения, распознавать намерение клиента и справляться с опечатками в тексте.',
    weights: [
      { label: '💬 Неформальный стиль (Q&A)',   source: 'qa_informal',     w: 0.30 },
      { label: '💬 Разговорный стиль (Q&A)',    source: 'qa_slang',        w: 0.15 },
      { label: '🏷 Классификация намерений',    source: 'cl_overall',      w: 0.35 },
      { label: '🔤 Устойчивость к опечаткам',  source: 'rb_overall',      w: 0.20 },
    ],
  },
  {
    id: 'legal',
    icon: '⚖️',
    name: 'Юридический отдел',
    desc: 'Юристы составляют договоры, официальные письма и проверяют правовые документы. ИИ должен писать грамотно в официальном стиле, точно знать факты и понимать сложные тексты.',
    weights: [
      { label: '💼 Официальный стиль (Q&A)',    source: 'qa_formal',       w: 0.40 },
      { label: '✅ Точность фактов',            source: 'fk_overall',      w: 0.35 },
      { label: '📖 Понимание документов',       source: 'rc_overall',      w: 0.25 },
    ],
  },
  {
    id: 'risk',
    icon: '🛡️',
    name: 'Управление рисками',
    desc: 'Риск-аналитики оценивают угрозы и составляют заключения. ИИ должен проверять факты, понимать аналитические отчёты и формулировать чёткие выводы.',
    weights: [
      { label: '✅ Точность фактов',            source: 'fk_overall',      w: 0.40 },
      { label: '📖 Понимание документов',       source: 'rc_overall',      w: 0.35 },
      { label: '💼 Официальный стиль (Q&A)',    source: 'qa_formal',       w: 0.25 },
    ],
  },
  {
    id: 'credit',
    icon: '💳',
    name: 'Кредитный отдел',
    desc: 'Кредитные аналитики работают с банковскими документами, оценивают заявки и составляют официальные заключения. Ключевые навыки — анализ текстов и официальная переписка.',
    weights: [
      { label: '📖 Понимание документов',       source: 'rc_overall',      w: 0.40 },
      { label: '💼 Официальный стиль (Q&A)',    source: 'qa_formal',       w: 0.35 },
      { label: '✅ Точность фактов',            source: 'fk_overall',      w: 0.25 },
    ],
  },
  {
    id: 'marketing',
    icon: '📢',
    name: 'Маркетинг',
    desc: 'Маркетологи пишут контент для соцсетей, рекламные тексты и общаются с молодой аудиторией. ИИ должен хорошо владеть разговорным языком и понимать настроение аудитории.',
    weights: [
      { label: '💬 Повседневный стиль (Q&A)',   source: 'qa_informal',     w: 0.35 },
      { label: '💬 Разговорный стиль (Q&A)',    source: 'qa_slang',        w: 0.35 },
      { label: '🏷 Классификация тональности', source: 'cl_sentiment',    w: 0.30 },
    ],
  },
  {
    id: 'hr',
    icon: '👥',
    name: 'HR / Кадровый отдел',
    desc: 'HR работает с сотрудниками на всех уровнях — от неформального общения до официальных приказов. ИИ должен одинаково хорошо писать и официально, и по-человечески.',
    weights: [
      { label: '💬 Повседневный стиль (Q&A)',   source: 'qa_informal',     w: 0.40 },
      { label: '🏷 Классификация намерений',    source: 'cl_overall',      w: 0.35 },
      { label: '💼 Официальный стиль (Q&A)',    source: 'qa_formal',       w: 0.25 },
    ],
  },
  {
    id: 'compliance',
    icon: '📋',
    name: 'Комплаенс',
    desc: 'Комплаенс-офицеры следят за соблюдением нормативов и проверяют документы на соответствие. ИИ должен знать законы и факты, понимать регуляторные тексты.',
    weights: [
      { label: '✅ Точность фактов',            source: 'fk_overall',      w: 0.45 },
      { label: '💼 Официальный стиль (Q&A)',    source: 'qa_formal',       w: 0.30 },
      { label: '📖 Понимание документов',       source: 'rc_overall',      w: 0.25 },
    ],
  },
  {
    id: 'digital',
    icon: '💻',
    name: 'IT / Цифровые услуги',
    desc: 'IT-специалисты и поддержка цифровых каналов. ИИ должен классифицировать технические обращения, понимать нестандартные сообщения и быть универсальным помощником.',
    weights: [
      { label: '🏷 Классификация обращений',    source: 'cl_overall',      w: 0.35 },
      { label: '🔤 Устойчивость к опечаткам',  source: 'rb_overall',      w: 0.30 },
      { label: '💬 Повседневный стиль (Q&A)',   source: 'qa_informal',     w: 0.35 },
    ],
  },
];

// Извлечь числовое значение источника из данных модели
function getDeptSourceScore(modelId, source, data) {
  const lb   = (data.leaderboard      || {})[modelId] || {};
  const cl   = (data.cl_leaderboard   || {})[modelId] || {};
  const rb   = (data.rb_leaderboard   || {})[modelId] || {};
  const fk   = (data.fk_leaderboard   || {})[modelId] || {};
  const rc   = (data.rc_leaderboard   || {})[modelId] || {};
  const lq   = (data.lq_leaderboard   || {})[modelId] || {};

  switch (source) {
    case 'qa_informal':  return lb.informal        ?? null;
    case 'qa_slang':     return lb.slang           ?? null;
    case 'qa_formal':    return lb.formal_business ?? null;
    case 'qa_overall':   return lb.overall         ?? null;
    case 'cl_overall':   return cl.overall         ?? null;
    case 'cl_sentiment': return cl.sentiment       ?? null;
    case 'rb_overall':   return rb.overall         ?? null;
    case 'fk_overall':   return fk.overall         ?? null;
    case 'rc_overall':   return rc.overall         ?? null;
    case 'lq_overall':   return lq.overall         ?? null;
    default:             return null;
  }
}

// Рассчитать взвешенный балл департамента для модели
function computeDeptScore(modelId, dept, data) {
  let totalWeight = 0;
  let totalScore  = 0;
  for (const { source, w } of dept.weights) {
    const val = getDeptSourceScore(modelId, source, data);
    if (val != null) {
      totalScore  += val * w;
      totalWeight += w;
    }
  }
  if (totalWeight < 0.3) return null; // недостаточно данных
  return totalScore / totalWeight;
}

// ── Рендер боковой панели со списком департаментов ──
function renderDeptsView() {
  const list = document.getElementById('deptList');
  if (!list) return;

  list.innerHTML = DEPARTMENTS.map(dept => `
    <div class="q-item dept-item" data-id="${dept.id}" onclick="selectDepartment('${dept.id}')">
      <div class="dept-item-icon">${dept.icon}</div>
      <div class="dept-item-body">
        <div class="dept-item-name">${dept.name}</div>
        <div class="dept-item-hint">${dept.weights.map(w => w.label.split(' ')[0]).join(' · ')}</div>
      </div>
    </div>`).join('');
}

// ── Выбрать департамент ──
function selectDepartment(deptId) {
  const data = state.appData;
  if (!data) return;

  const dept = DEPARTMENTS.find(d => d.id === deptId);
  if (!dept) return;

  document.querySelectorAll('#deptList .dept-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === deptId)
  );

  // Собрать все модели и рассчитать баллы
  const allModels = new Set([
    ...Object.keys(data.models || {}),
    ...Object.keys(data.leaderboard || {}),
    ...Object.keys(data.cl_leaderboard || {}),
    ...Object.keys(data.rb_leaderboard || {}),
    ...Object.keys(data.fk_leaderboard || {}),
    ...Object.keys(data.rc_leaderboard || {}),
  ]);

  // Убрать устаревшие модели (grok-2 → grok-3)
  const filteredModels = [...allModels].filter(id => {
    const newerId = MODEL_SUPERSEDED_BY[id];
    return !(newerId && allModels.has(newerId));
  });

  const ranked = filteredModels
    .map(id => ({ id, score: computeDeptScore(id, dept, data), meta: getModelMeta(id, data) }))
    .filter(m => m.score != null)
    .sort((a, b) => b.score - a.score);

  const content = document.getElementById('deptContent');
  if (!content) return;

  const medals = ['🥇', '🥈', '🥉'];

  const rows = ranked.map((m, i) => {
    const medal = i < 3 ? medals[i] : `#${i + 1}`;
    const scores = dept.weights.map(({ label, source }) => {
      const val = getDeptSourceScore(m.id, source, data);
      return val != null
        ? `<div class="dept-sub-score">
             <span class="dept-sub-label">${label}</span>
             <div class="dept-sub-bar-wrap">
               <div class="dept-sub-bar" style="width:${Math.min(val,100)}%;background:${m.meta.color}"></div>
             </div>
             <span class="dept-sub-val ${scoreClass(val)}">${Math.round(val)}</span>
           </div>`
        : `<div class="dept-sub-score">
             <span class="dept-sub-label">${label}</span>
             <span class="dept-sub-na">нет данных</span>
           </div>`;
    }).join('');

    return `
      <div class="dept-model-card ${i === 0 ? 'dept-card-top' : ''}">
        <div class="dept-card-header">
          <div class="dept-card-rank">${medal}</div>
          <div class="dept-card-info" onclick="openModelDrawer('${m.id}')" style="cursor:pointer">
            <div class="dept-card-dot" style="background:${m.meta.color}"></div>
            <div>
              <div class="dept-card-name">${escHtml(m.meta.name)}</div>
              <div class="dept-card-provider">
                ${escHtml(m.meta.provider)}
                <span class="type-badge type-${m.meta.type}">
                  ${m.meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
                </span>
              </div>
            </div>
          </div>
          <div class="dept-card-score-box">
            <div class="dept-card-score ${scoreClass(m.score)}">${Math.round(m.score)}</div>
            <div class="dept-card-score-label">Балл</div>
          </div>
        </div>
        <div class="dept-card-breakdown">${scores}</div>
      </div>`;
  }).join('');

  content.innerHTML = `
    <div class="dept-detail">
      <div class="dept-detail-header">
        <div class="dept-header-icon">${dept.icon}</div>
        <div>
          <h2 class="dept-header-name">${dept.name}</h2>
          <p class="dept-header-desc">${dept.desc}</p>
        </div>
      </div>

      <div class="dept-criteria">
        <div class="dept-criteria-title">Критерии подбора:</div>
        <div class="dept-criteria-chips">
          ${dept.weights.map(w => `
            <div class="dept-criteria-chip">
              <span class="dept-criteria-label">${w.label}</span>
              <span class="dept-criteria-weight">${Math.round(w.w * 100)}%</span>
            </div>`).join('')}
        </div>
      </div>

      <div class="dept-models-title">
        Рейтинг AI-моделей для «${dept.name}» · ${ranked.length} моделей
      </div>
      <div class="dept-models-list">${rows}</div>
    </div>`;
}
