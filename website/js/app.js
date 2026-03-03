// ═══════════════════════════════════════════════════════════════
// ULAB Dashboard — app.js
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

const DIFF_LABELS = {
  basic:        'Начальный',
  intermediate: 'Средний',
  advanced:     'Продвинутый',
};

const DIM_INFO = {
  D1: { name: 'Точность ответа',    tooltip: 'Насколько ответ правильно и полно отвечает на заданный вопрос' },
  D2: { name: 'Качество языка',     tooltip: 'Грамматика, орфография и правильность узбекского языка' },
  D3: { name: 'Соответствие стилю', tooltip: 'Насколько стиль ответа соответствует требуемому регистру' },
  D4: { name: 'Естественность речи',tooltip: 'Звучит ли ответ как живой человек, а не машинный перевод' },
};

// Fallback метаданные для моделей, которые есть только в модулях
const MODEL_FALLBACK = {
  'gemini-flash': { name: 'Gemini 2.0 Flash', provider: 'Google',    color: '#4285F4', type: 'commercial' },
  'grok-3':       { name: 'Grok 3',           provider: 'xAI',       color: '#1d9bf0', type: 'commercial' },
  'grok-2':       { name: 'Grok 2',           provider: 'xAI',       color: '#1d9bf0', type: 'commercial' },
};

// ── Состояние ──────────────────────────────────────────────────
const state = {
  activeView:       'rating',
  activeRegister:   'all',
  selectedId:       null,
  search:           '',
  showModules:      false,
  lbRanked:         [],
  appData:          null,
  compareMode:      false,
  compareSelected:  new Set(),
  contestedOnly:    false,
  usecaseFilter:    'all',
};

// ── Инициализация ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const data = window.BENCHMARK_RESULTS;

  if (!data || !data.questions || !data.questions.length) {
    document.getElementById('noDataBanner').style.display = 'flex';
    document.getElementById('statusText').textContent = 'Данные не найдены';
    return;
  }

  state.appData = data;
  document.getElementById('app').style.display = 'flex';

  // Заголовок
  const date = data.benchmark_date || '—';
  document.getElementById('benchDate').textContent = `Дата тестирования: ${date}`;
  const modelCount = Object.keys(data.models || {}).length;
  document.getElementById('modelCount').textContent = modelCount;

  const scored = data.scored_at ? ` · Оценено: ${data.scored_at}` : '';
  document.getElementById('statusText').textContent =
    `${data.questions.length} вопросов · ${modelCount} моделей${scored}`;

  // REQ-7: Print date footer
  const printDateEl = document.getElementById('printDate');
  if (printDateEl) printDateEl.textContent = data.scored_at || data.benchmark_date || new Date().toISOString().slice(0, 10);

  // Счётчики вкладок
  const q = data.questions;
  document.getElementById('cnt-all').textContent      = q.length;
  document.getElementById('cnt-formal').textContent   = q.filter(x => x.register === 'formal_business').length;
  document.getElementById('cnt-informal').textContent = q.filter(x => x.register === 'informal').length;
  document.getElementById('cnt-slang').textContent    = q.filter(x => x.register === 'slang').length;

  setupNavigation(data);
  setupSearch(data);
  setupTooltips();
  renderRatingView(data);
});

// ── Навигация ──────────────────────────────────────────────────
function setupNavigation(data) {
  document.querySelectorAll('.nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const view = btn.dataset.view;

      document.getElementById('ratingView').style.display    = 'none';
      document.getElementById('tasksView').style.display     = 'none';
      document.getElementById('questionsView').style.display = 'none';

      if (view === 'rating') {
        state.activeView = 'rating';
        document.getElementById('ratingView').style.display = 'block';

      } else if (view === 'tasks') {
        state.activeView = 'tasks';
        // REQ-2: reset use-case filter when entering tasks tab
        state.usecaseFilter = 'all';
        document.getElementById('tasksView').style.display = 'block';
        renderTasksView(data);

      } else {
        state.activeView     = 'questions';
        state.activeRegister = view;
        state.selectedId     = null;
        state.search         = '';
        state.contestedOnly  = false;
        state.compareMode    = false;
        state.compareSelected.clear();
        document.getElementById('searchInput').value = '';
        const toggleEl = document.getElementById('contestedToggle');
        if (toggleEl) toggleEl.checked = false;
        document.getElementById('questionsView').style.display = 'flex';

        const titles = {
          all:             'Все вопросы (60)',
          slang:           'Разговорный стиль (20 вопросов)',
          informal:        'Повседневный стиль (20 вопросов)',
          formal_business: 'Официальный деловой стиль (20 вопросов)',
        };
        document.getElementById('sidebarTitle').textContent = titles[view] || 'Вопросы';

        renderQuestionList(data);
        document.getElementById('contentArea').innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">←</div>
            <p>Выберите вопрос из списка слева, чтобы увидеть ответы всех AI-моделей</p>
          </div>`;
      }
    });
  });
}

// ── Поиск ──────────────────────────────────────────────────────
function setupSearch(data) {
  document.getElementById('searchInput').addEventListener('input', e => {
    state.search = e.target.value.toLowerCase();
    renderQuestionList(data);
  });
}

// ── Утилита: метаданные модели ─────────────────────────────────
function getModelMeta(modelId, data) {
  return (data.models || {})[modelId]
      || MODEL_FALLBACK[modelId]
      || { name: modelId, provider: '—', color: '#888', type: 'unknown' };
}

// ─── REQ-6: Проверка флага устойчивости к шуму ────────────────
function hasRobustnessWarning(modelId, data) {
  const rbLb   = (data || state.appData || {}).rb_leaderboard || {};
  const coreLb = (data || state.appData || {}).leaderboard    || {};
  const rbEntry = rbLb[modelId];
  if (!rbEntry || rbEntry.overall == null) return false;
  const overall = coreLb[modelId]?.overall;
  if (overall == null) return false;
  return (overall - rbEntry.overall) > 15;
}

function robustnessWarningIcon(modelId, data) {
  if (!hasRobustnessWarning(modelId, data)) return '';
  const rbLb   = (data || state.appData || {}).rb_leaderboard || {};
  const coreLb = (data || state.appData || {}).leaderboard    || {};
  const rb      = Math.round(rbLb[modelId].overall);
  const overall = Math.round(coreLb[modelId].overall);
  const meta    = getModelMeta(modelId, data || state.appData || {});
  const tip     = `${escHtml(meta.name)} значительно хуже справляется с зашумлёнными текстами (RB: ${rb} vs Общий: ${overall}). Не рекомендуется для неструктурированных каналов.`;
  return ` <span class="rb-warn-icon" data-tooltip="${tip}" title="${tip}">⚠️</span>`;
}

// ═══════════════════════════════════════════════════════════════
// СТРАНИЦА РЕЙТИНГА
// ═══════════════════════════════════════════════════════════════

function renderRatingView(data) {
  if (!data.leaderboard) return;

  const ranked = Object.entries(data.leaderboard)
    .map(([id, sc]) => ({ id, ...sc, meta: getModelMeta(id, data) }))
    .filter(m => m.overall != null)
    .sort((a, b) => (b.overall || 0) - (a.overall || 0));

  state.lbRanked = ranked;

  renderExecSummary(ranked, data);
  renderHero(ranked);
  renderLeaderboardTable(ranked, data);
  renderInsights(data);
  setupLbFilter(ranked, data);
}

// ── REQ-1: Executive Summary Card ─────────────────────────────
function renderExecSummary(ranked, data) {
  const el = document.getElementById('execSummary');
  if (!el || !ranked.length) return;

  const top   = ranked[0];
  const second = ranked[1];
  const gap   = second ? (top.overall - second.overall) : null;

  const fkLb = (data || {}).fk_leaderboard || {};
  const fkRanked = Object.entries(fkLb)
    .filter(([, s]) => s.overall != null)
    .sort((a, b) => b[1].overall - a[1].overall);
  const formalRanked = Object.entries(data.leaderboard || {})
    .filter(([, s]) => s.formal_business != null)
    .sort((a, b) => b[1].formal_business - a[1].formal_business);

  const recModelId = formalRanked.length ? formalRanked[0][0] : top.id;
  const recName    = getModelMeta(recModelId, data).name;

  const modelCount  = Object.keys(data.models || {}).length;
  const moduleCount = [data.cl_leaderboard, data.rb_leaderboard, data.fk_leaderboard, data.rc_leaderboard]
    .filter(Boolean).length + 1;
  const qCount = (data.questions || []).length;

  el.innerHTML = `
    <div class="exec-winner">
      <span class="exec-winner-label">Победитель</span>
      <span class="exec-winner-name">${escHtml(top.meta.name)}</span>
      <span class="exec-winner-score">${Math.round(top.overall)}</span>
    </div>
    ${gap != null ? `<div class="exec-gap">+${gap.toFixed(1)} впереди</div>` : ''}
    <div class="exec-rec">Рекомендуется: ${escHtml(recName)} — наивысший балл в официальном стиле и проверке фактов</div>
    <div class="exec-conf">На основе ${qCount} вопросов · ${moduleCount} модулей · ${modelCount} моделей</div>`;
}

function setupLbFilter(ranked, data) {
  document.querySelectorAll('.lb-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.lb-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      let filtered = ranked;
      if (filter === 'commercial') filtered = ranked.filter(m => m.meta.type === 'commercial');
      else if (filter === 'opensource') filtered = ranked.filter(m => m.meta.type !== 'commercial');
      renderLeaderboardTable(filtered, data);
    });
  });
}

// ── Герой-секция (победитель) ──────────────────────────────────
function renderHero(ranked) {
  const hero = document.getElementById('heroSection');
  if (!ranked.length) { hero.innerHTML = ''; return; }

  const w = ranked[0];
  const s = ranked[1];
  const t = ranked[2];

  const winner = `
    <div class="hero-winner">
      <div class="hero-medal">🥇</div>
      <div class="hero-body">
        <div class="hero-eyebrow">ЛУЧШАЯ МОДЕЛЬ ПО РЕЗУЛЬТАТАМ ТЕСТИРОВАНИЯ</div>
        <div class="hero-name">${escHtml(w.meta.name)}</div>
        <div class="hero-provider">
          ${escHtml(w.meta.provider || '')} &nbsp;·&nbsp;
          ${w.meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
        </div>
        <div class="hero-reg-bars">
          ${heroBar('Официальный стиль', w.formal_business)}
          ${heroBar('Повседневный',       w.informal)}
          ${heroBar('Разговорный',        w.slang)}
        </div>
      </div>
      <div class="hero-score">
        <div class="hero-score-num">${Math.round(w.overall)}</div>
        <div class="hero-score-label">из 100</div>
      </div>
    </div>`;

  const runnerCard = (m, medal) => !m ? '' : `
    <div class="hero-runner" style="--runner-color:${m.meta.color}">
      <div class="runner-medal">${medal}</div>
      <div class="runner-info">
        <div class="runner-name">${escHtml(m.meta.name)}</div>
        <div class="runner-provider">${escHtml(m.meta.provider || '')}</div>
      </div>
      <div class="runner-score">${Math.round(m.overall)}<span>&nbsp;/ 100</span></div>
    </div>`;

  hero.innerHTML = `
    <div class="hero-layout">
      ${winner}
      <div class="hero-runners">
        ${runnerCard(s, '🥈')}
        ${runnerCard(t, '🥉')}
      </div>
    </div>`;
}

function heroBar(label, val) {
  if (val == null) return '';
  return `
    <div class="hero-reg-row">
      <span class="hero-reg-label">${label}</span>
      <div class="hero-reg-track">
        <div class="hero-reg-fill" style="width:${Math.min(val,100)}%"></div>
      </div>
      <span class="hero-reg-val">${Math.round(val)}</span>
    </div>`;
}

// ── Таблица рейтинга с модульными колонками ────────────────────
function renderLeaderboardTable(ranked, data) {
  const d    = data || state.appData || {};
  const clLb = d.cl_leaderboard || {};
  const rbLb = d.rb_leaderboard || {};
  const fkLb = d.fk_leaderboard || {};
  const rcLb = d.rc_leaderboard || {};

  const show   = state.showModules;
  const medals = ['🥇', '🥈', '🥉'];

  // REQ-4: delta is vs the #1 model in the current filtered list
  const topScore = ranked.length ? ranked[0].overall : null;

  const rows = ranked.map((m, i) => {
    const bg = i === 0 ? 'rgba(245,158,11,0.05)'
             : i === 1 ? 'rgba(148,163,184,0.05)'
             : i === 2 ? 'rgba(180,83,9,0.05)' : '';
    const rankCell = i < 3
      ? `<span class="rank-medal">${medals[i]}</span>`
      : `<span class="rank-num">#${i + 1}</span>`;

    // REQ-6: Robustness warning icon
    const warnIcon = robustnessWarningIcon(m.id, d);

    // Модульные баллы
    const cl = clLb[m.id]?.overall;
    const rb = rbLb[m.id]?.overall;
    const fk = fkLb[m.id]?.overall;
    const rc = rcLb[m.id]?.overall;

    // REQ-4: delta column
    const deltaCell = deltaVsTop(m.overall, topScore);

    // REQ-5: stacked register bar
    const stackedBar = regStackedBarCell(m.formal_business, m.informal, m.slang);

    const modCols = show ? `
      ${modCell(cl)}
      ${modCell(rb)}
      ${modCell(fk)}
      ${modCell(rc)}` : '';

    // REQ-5: individual reg columns shown only when modules are expanded (plus stacked bar always)
    const indivRegCols = show ? `
      ${regBarCell(m.formal_business)}
      ${regBarCell(m.informal)}
      ${regBarCell(m.slang)}` : '';

    return `
      <tr${bg ? ` style="background:${bg}"` : ''}>
        <td class="td-rank">${rankCell}</td>
        <td class="td-model">
          <div class="model-cell model-cell-clickable" onclick="openModelDrawer('${m.id}', window.BENCHMARK_RESULTS)" title="Подробная карточка модели">
            <div class="model-dot" style="background:${m.meta.color}"></div>
            <div>
              <div class="model-name">${escHtml(m.meta.name)}${warnIcon}</div>
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
        <td class="td-overall">
          <span class="overall-score ${scoreClass(m.overall)}">${Math.round(m.overall)}</span>
        </td>
        ${deltaCell}
        ${stackedBar}
        ${indivRegCols}
        ${modCols}
      </tr>`;
  }).join('');

  const modHeaders = show ? `
    <th class="th-mod" title="Classification">CL</th>
    <th class="th-mod" title="Robustness">RB</th>
    <th class="th-mod" title="Fact-check">FK</th>
    <th class="th-mod" title="Reading Comprehension">RC</th>` : '';

  const indivRegHeaders = show ? `
    <th>Официальный стиль</th>
    <th>Повседневный стиль</th>
    <th>Разговорный стиль</th>` : '';

  document.getElementById('lbTable').innerHTML = `
    <thead>
      <tr>
        <th class="th-rank">#</th>
        <th>Модель</th>
        <th class="th-center">Итоговый балл</th>
        <th class="th-center th-delta">vs #1</th>
        <th class="th-center">Стили</th>
        ${indivRegHeaders}
        ${modHeaders}
      </tr>
    </thead>
    <tbody>${rows}</tbody>`;
}

// REQ-4: delta cell
function deltaVsTop(score, topScore) {
  if (topScore == null || score == null) {
    return `<td class="td-delta"><span class="delta-none">—</span></td>`;
  }
  const delta = score - topScore;
  if (Math.abs(delta) < 0.05) {
    return `<td class="td-delta"><span class="delta-none">—</span></td>`;
  }
  const formatted = delta.toFixed(1);
  return `<td class="td-delta"><span class="delta-neg">${formatted}</span></td>`;
}

// REQ-5: stacked register bar cell
function regStackedBarCell(formal, informal, slang) {
  if (formal == null && informal == null && slang == null) {
    return `<td class="td-reg-bar"><span class="na-text">Нет данных</span></td>`;
  }
  const f = Math.max(0, Math.min(100, formal  || 0));
  const i = Math.max(0, Math.min(100, informal || 0));
  const s = Math.max(0, Math.min(100, slang    || 0));
  const tip = `Офиц: ${Math.round(formal ?? 0)} · Повседн: ${Math.round(informal ?? 0)} · Разгов: ${Math.round(slang ?? 0)}`;
  return `
    <td class="td-reg-bar">
      <div class="reg-stacked-bar" data-tooltip="${escHtml(tip)}" title="${escHtml(tip)}">
        <div class="reg-stacked-seg seg-formal"  style="width:${f * 1.2}px" title="Офиц: ${Math.round(f)}"></div>
        <div class="reg-stacked-seg seg-informal" style="width:${i * 1.2}px" title="Повседн: ${Math.round(i)}"></div>
        <div class="reg-stacked-seg seg-slang"   style="width:${s * 1.2}px" title="Разгов: ${Math.round(s)}"></div>
      </div>
    </td>`;
}

function modCell(val) {
  if (val == null) return `<td class="td-mod"><span class="na-text">—</span></td>`;
  return `<td class="td-mod"><span class="mod-badge ${scoreClass(val)}">${Math.round(val)}</span></td>`;
}

function regBarCell(val) {
  if (val == null) return `<td class="td-reg"><span class="na-text">Нет данных</span></td>`;
  const cls = scoreClass(val);
  return `
    <td class="td-reg">
      <div class="reg-cell">
        <div class="reg-bar-track">
          <div class="reg-bar-fill ${cls}" style="width:${Math.min(val,100)}%"></div>
        </div>
        <span class="reg-val ${cls}">${Math.round(val)}</span>
      </div>
    </td>`;
}

// ── Переключатель модульных колонок ───────────────────────────
function toggleModuleColumns() {
  state.showModules = !state.showModules;
  const btn = document.getElementById('modulesToggleBtn');
  btn.textContent = state.showModules ? '− Скрыть модули' : '+ Показать модули';
  btn.classList.toggle('active', state.showModules);

  const activeFilter = document.querySelector('.lb-tab.active')?.dataset.filter || 'all';
  let filtered = state.lbRanked;
  if (activeFilter === 'commercial') filtered = state.lbRanked.filter(m => m.meta.type === 'commercial');
  else if (activeFilter === 'opensource') filtered = state.lbRanked.filter(m => m.meta.type !== 'commercial');
  renderLeaderboardTable(filtered, state.appData);
}

// ── Ключевые выводы ────────────────────────────────────────────
function renderInsights(data) {
  const lb     = data.leaderboard;
  const models = data.models;
  const insights = [];

  const formalRanked = Object.entries(lb)
    .filter(([, s]) => s.formal_business != null)
    .sort((a, b) => b[1].formal_business - a[1].formal_business);

  if (formalRanked.length) {
    const [bestId, bestSc] = formalRanked[0];
    const name = models[bestId]?.name || bestId;
    insights.push({
      icon: '🏦', title: 'Лучшая модель для банка',
      text: `<strong>${escHtml(name)}</strong> показала наивысший балл в официальном деловом стиле — <strong>${Math.round(bestSc.formal_business)} из 100</strong>. Рекомендуется для официальной переписки, клиентского сервиса и деловых документов.`,
      type: 'positive',
    });
  }

  const gaps = Object.entries(lb)
    .filter(([, s]) => s.slang != null && s.informal != null && s.formal_business != null)
    .map(([id, s]) => {
      const vals = [s.slang, s.informal, s.formal_business];
      return { id, gap: Math.max(...vals) - Math.min(...vals) };
    })
    .sort((a, b) => b.gap - a.gap);

  if (gaps.length) {
    const gm   = gaps[0];
    const name = models[gm.id]?.name || gm.id;
    insights.push({
      icon: '📊', title: 'Наибольший разброс результатов',
      text: `<strong>${escHtml(name)}</strong> показывает нестабильные результаты — разрыв между лучшим и худшим стилем составляет <strong>${Math.round(gm.gap)} баллов</strong>. Это говорит о зависимости качества от типа запроса.`,
      type: 'warning',
    });
  }

  const regAvgs = {
    'официальном деловом стиле': avgArr(Object.values(lb).map(s => s.formal_business).filter(v => v != null)),
    'повседневном стиле':         avgArr(Object.values(lb).map(s => s.informal).filter(v => v != null)),
    'разговорном стиле (слэнг)': avgArr(Object.values(lb).map(s => s.slang).filter(v => v != null)),
  };
  const [hardestName, hardestVal] = Object.entries(regAvgs).sort((a, b) => a[1] - b[1])[0];
  insights.push({
    icon: '💡', title: 'Самый сложный стиль',
    text: `Все модели в среднем слабее всего справляются с <strong>${hardestName}</strong> — средний балл <strong>${Math.round(hardestVal)} из 100</strong>. Это наименее освоенная область для всех тестируемых AI-ассистентов.`,
    type: 'info',
  });

  if (data.fk_leaderboard) {
    const fkEntries = Object.entries(data.fk_leaderboard).filter(([, s]) => s.overall != null);
    if (fkEntries.length) {
      const perfect = fkEntries.filter(([, s]) => s.overall >= 100).length;
      insights.push({
        icon: '✅', title: 'Проверка фактов',
        text: `<strong>${perfect} из ${fkEntries.length}</strong> протестированных моделей правильно оценили все факты об Узбекистане и банковской системе. Задание включало распознавание распространённых галлюцинаций.`,
        type: 'positive',
      });
    }
  }

  document.getElementById('insightsGrid').innerHTML = insights.map(ins => `
    <div class="insight-card insight-${ins.type}">
      <div class="insight-icon">${ins.icon}</div>
      <div class="insight-title">${ins.title}</div>
      <div class="insight-text">${ins.text}</div>
    </div>`).join('');
}

// ═══════════════════════════════════════════════════════════════
// СТРАНИЦА ЗАДАНИЙ
// ═══════════════════════════════════════════════════════════════

const TASK_MODULES = [
  {
    key: 'cl', icon: '🏷', title: 'Классификация текста (CL)',
    desc: '20 вопросов — определение тональности, намерения и регистра речи клиента банка',
    lbKey: 'cl_leaderboard',
    subtypes: [
      { key: 'sentiment', label: 'Тональность' },
      { key: 'intent',    label: 'Намерение' },
      { key: 'register',  label: 'Регистр' },
    ],
  },
  {
    key: 'rb', icon: '🔊', title: 'Устойчивость к шуму (RB)',
    desc: '15 вопросов — определение намерения при зашумлённом тексте (опечатки, кириллица, апострофы)',
    lbKey: 'rb_leaderboard',
    subtypes: [
      { key: 'apostrophe_drop', label: 'Без апострофов' },
      { key: 'typo',            label: 'Опечатки' },
      { key: 'cyrillic_mix',   label: 'Кириллица' },
    ],
  },
  {
    key: 'fk', icon: '✅', title: 'Проверка фактов (FK)',
    desc: '10 вопросов — выявление галлюцинаций о стране, валюте и банковской системе Узбекистана',
    lbKey: 'fk_leaderboard',
    subtypes: [
      { key: 'country',  label: 'Страна' },
      { key: 'currency', label: 'Валюта' },
      { key: 'banking',  label: 'Банкинг' },
    ],
  },
  {
    key: 'rc', icon: '📖', title: 'Понимание текста (RC)',
    desc: '9 вопросов — тест на понимание реальных банковских новостных текстов с kun.uz',
    lbKey: 'rc_leaderboard',
    subtypes: [
      { key: 'hayot_bank',    label: 'Hayot Bank' },
      { key: 'kredit_freeze', label: 'Freeze сервис' },
      { key: 'pul_otkazma',   label: 'Пул ўтказмалари' },
    ],
  },
];

const MODULE_TOP_N = 5;

// REQ-2: Use-Case filter configuration
const USECASE_OPTIONS = [
  { key: 'all',            label: 'Все модули',       highlight: [] },
  { key: 'client_service', label: 'Клиентский сервис', highlight: ['cl', 'rb'] },
  { key: 'risk',           label: 'Риски',             highlight: ['fk'] },
  { key: 'compliance',     label: 'Комплаенс',         highlight: ['fk', 'rc'] },
  { key: 'digital',        label: 'Цифровые каналы',   highlight: ['rb'] },
];

function renderUsecaseFilter(data) {
  const container = document.getElementById('usecaseFilter');
  if (!container) return;

  container.innerHTML = USECASE_OPTIONS.map(opt => `
    <button class="usecase-pill ${state.usecaseFilter === opt.key ? 'active' : ''}"
            onclick="applyUsecaseFilter('${opt.key}')">
      ${escHtml(opt.label)}
    </button>`).join('');
}

function applyUsecaseFilter(key) {
  state.usecaseFilter = key;
  renderUsecaseFilter(state.appData);
  reorderTaskCards(state.appData);
}

function reorderTaskCards(data) {
  const opt = USECASE_OPTIONS.find(o => o.key === state.usecaseFilter) || USECASE_OPTIONS[0];
  const highlighted = opt.highlight;

  const ordered = [
    ...TASK_MODULES.filter(m => highlighted.includes(m.key)),
    ...TASK_MODULES.filter(m => !highlighted.includes(m.key)),
  ];

  const grid = document.getElementById('tasksGrid');
  grid.innerHTML = ordered.map(mod => buildModuleCard(mod, data, highlighted.includes(mod.key))).join('');
}

function buildModuleCard(mod, data, isHighlighted) {
  const lb = data[mod.lbKey];
  if (!lb) return `
    <div class="module-card${isHighlighted ? ' module-card-highlighted' : ''}">
      <div class="module-card-header">
        <div class="module-card-icon">${mod.icon}</div>
        <div>
          <div class="module-card-title">${mod.title}</div>
          <div class="module-card-desc">${mod.desc}</div>
        </div>
      </div>
      <p class="no-data-msg">Данные не найдены — запустите run_benchmark_${mod.key}.py</p>
    </div>`;

  const ranked = Object.entries(lb)
    .filter(([, s]) => s.overall != null)
    .sort((a, b) => (b[1].overall || 0) - (a[1].overall || 0));

  const medals  = ['🥇','🥈','🥉'];
  const topN    = ranked.slice(0, MODULE_TOP_N);

  const rows = topN.map(([modelId, s], i) => {
    const meta = getModelMeta(modelId, data);
    const subCells = mod.subtypes.map(st => {
      const v = s[st.key];
      return v != null
        ? `<td class="td-mod-sub ${scoreClass(v)}">${Math.round(v)}</td>`
        : `<td class="td-mod-sub na-text">—</td>`;
    }).join('');

    return `
      <tr>
        <td class="td-rank">${i < 3 ? medals[i] : `<span class="rank-num">#${i+1}</span>`}</td>
        <td class="td-model">
          <div class="model-cell model-cell-clickable" onclick="openModelDrawer('${modelId}', window.BENCHMARK_RESULTS)" title="Карточка модели">
            <div class="model-dot" style="background:${meta.color}"></div>
            <div class="model-name" style="font-size:13px">${escHtml(meta.name)}</div>
          </div>
        </td>
        <td class="td-overall">
          <span class="overall-score ${scoreClass(s.overall)}">${Math.round(s.overall)}</span>
        </td>
        ${subCells}
      </tr>`;
  }).join('');

  const thSubs    = mod.subtypes.map(st => `<th class="th-sub">${st.label}</th>`).join('');
  const allPerfect = ranked.filter(([,s]) => s.overall >= 100).length;
  const avgScore  = Math.round(avgArr(ranked.map(([,s]) => s.overall)));
  const remaining = ranked.length - MODULE_TOP_N;

  // REQ-2: highlight banner with best model for this module
  const highlightBanner = isHighlighted && ranked.length ? (() => {
    const [topId] = ranked[0];
    const topMeta = getModelMeta(topId, data);
    return `<div class="module-highlight-banner">Лучшее для этого отдела: ${escHtml(topMeta.name)}</div>`;
  })() : '';

  return `
    <div class="module-card${isHighlighted ? ' module-card-highlighted' : ''}">
      ${highlightBanner}
      <div class="module-card-header">
        <div class="module-card-icon">${mod.icon}</div>
        <div>
          <div class="module-card-title">${mod.title}</div>
          <div class="module-card-desc">${mod.desc}</div>
        </div>
        <div class="module-card-stats">
          <div class="module-stat"><span class="module-stat-val">${ranked.length}</span><span class="module-stat-lbl">моделей</span></div>
          <div class="module-stat"><span class="module-stat-val ${scoreClass(avgScore)}">${avgScore}</span><span class="module-stat-lbl">ср. балл</span></div>
          ${allPerfect > 0 ? `<div class="module-stat"><span class="module-stat-val score-green">${allPerfect}</span><span class="module-stat-lbl">× 100%</span></div>` : ''}
        </div>
      </div>
      <div class="table-wrap">
        <table class="lb-table module-lb-table">
          <thead><tr>
            <th class="th-rank">#</th>
            <th>Модель</th>
            <th class="th-center">Итог</th>
            ${thSubs}
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      ${remaining > 0 ? `<div class="module-card-more">+ ещё ${remaining} моделей — нажмите [+ Показать модули] в рейтинге</div>` : ''}
    </div>`;
}

function renderTasksView(data) {
  renderUsecaseFilter(data);
  reorderTaskCards(data);
}

// ═══════════════════════════════════════════════════════════════
// КАРТОЧКА МОДЕЛИ — DRAWER + RADAR CHART
// ═══════════════════════════════════════════════════════════════

function openModelDrawer(modelId, data) {
  if (!data) return;
  state.drawerModelId = modelId;

  const meta = getModelMeta(modelId, data);
  const core = (data.leaderboard      || {})[modelId] || {};
  const cl   = (data.cl_leaderboard   || {})[modelId] || {};
  const rb   = (data.rb_leaderboard   || {})[modelId] || {};
  const fk   = (data.fk_leaderboard   || {})[modelId] || {};
  const rc   = (data.rc_leaderboard   || {})[modelId] || {};

  const radarLabels = ['Офиц.стиль', 'Повседн.', 'Разговор.', 'CL', 'RB', 'FK', 'RC', 'Общий'];
  const radarValues = [
    core.formal_business ?? null,
    core.informal        ?? null,
    core.slang           ?? null,
    cl.overall           ?? null,
    rb.overall           ?? null,
    fk.overall           ?? null,
    rc.overall           ?? null,
    core.overall         ?? null,
  ];

  const scoreRows = [
    { label: 'Общий балл (60 вопросов)', val: core.overall },
    { label: 'Официальный стиль',        val: core.formal_business },
    { label: 'Повседневный стиль',       val: core.informal },
    { label: 'Разговорный стиль',        val: core.slang },
    { label: 'Классификация (CL)',       val: cl.overall },
    { label: 'Устойчивость к шуму (RB)', val: rb.overall },
    { label: 'Проверка фактов (FK)',     val: fk.overall },
    { label: 'Понимание текста (RC)',    val: rc.overall },
  ].filter(r => r.val != null);

  // REQ-6: warning in drawer header
  const warnIcon = robustnessWarningIcon(modelId, data);

  document.getElementById('drawerContent').innerHTML = `
    <div class="drawer-model-header" style="border-left:4px solid ${meta.color}">
      <div class="drawer-model-dot" style="background:${meta.color}"></div>
      <div>
        <div class="drawer-model-name">${escHtml(meta.name)}${warnIcon}</div>
        <div class="drawer-model-sub">
          ${escHtml(meta.provider || '')}
          <span class="type-badge type-${meta.type}" style="margin-left:6px">
            ${meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
          </span>
        </div>
      </div>
    </div>

    <div class="drawer-radar-wrap">
      <canvas id="radarChart" width="300" height="300"></canvas>
    </div>

    <div class="drawer-scores">
      <div class="drawer-scores-title">Детализация по модулям</div>
      ${scoreRows.map(r => `
        <div class="drawer-score-row">
          <span class="drawer-score-label">${r.label}</span>
          <div class="drawer-score-bar-wrap">
            <div class="drawer-score-bar" style="width:${Math.min(r.val,100)}%;background:${meta.color}"></div>
          </div>
          <span class="drawer-score-val ${scoreClass(r.val)}">${Math.round(r.val)}</span>
        </div>`).join('')}
    </div>`;

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
        pointBackgroundColor: displayValues.map((v, i) => values[i] == null ? 'rgba(0,0,0,0.15)' : color),
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
        tooltip: {
          callbacks: {
            label: ctx => ` ${Math.round(ctx.raw)} / 100`,
          },
        },
      },
      animation: { duration: 500, easing: 'easeOutQuart' },
    },
  });
}

function hexToRgba(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(100,100,100,${alpha})`;
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ═══════════════════════════════════════════════════════════════
// СТРАНИЦА ВОПРОСОВ
// ═══════════════════════════════════════════════════════════════

// REQ-8: contested toggle handler
function onContestedToggle() {
  const el = document.getElementById('contestedToggle');
  state.contestedOnly = el ? el.checked : false;
  renderQuestionList(state.appData);
}

function getFilteredQuestions(data) {
  let questions = data.questions;
  const reg = state.activeRegister;

  if (reg !== 'all') questions = questions.filter(q => q.register === reg);
  if (state.search)  questions = questions.filter(q =>
    q.text.toLowerCase().includes(state.search) ||
    q.id.toLowerCase().includes(state.search)
  );

  // REQ-8: contested filter — spread (max - min score across models) > 30
  if (state.contestedOnly) {
    questions = questions.filter(q => {
      const scores = Object.values(q.responses || {})
        .map(r => r.scores?.total)
        .filter(t => t != null);
      if (scores.length < 2) return false;
      return (Math.max(...scores) - Math.min(...scores)) > 30;
    });
  }

  return questions;
}

function renderQuestionList(data) {
  const questions = getFilteredQuestions(data);
  const totalBeforeContested = (() => {
    let base = data.questions;
    const reg = state.activeRegister;
    if (reg !== 'all') base = base.filter(q => q.register === reg);
    if (state.search)  base = base.filter(q =>
      q.text.toLowerCase().includes(state.search) ||
      q.id.toLowerCase().includes(state.search)
    );
    return base.length;
  })();

  // REQ-8: update count label
  const countEl = document.getElementById('qListCount');
  if (countEl) {
    countEl.textContent = state.contestedOnly
      ? `Показано: ${questions.length} из ${totalBeforeContested}`
      : `Показано: ${questions.length} из ${totalBeforeContested}`;
  }

  const list = document.getElementById('questionList');
  if (!questions.length) {
    list.innerHTML = '<div class="q-empty">Ничего не найдено.<br>Попробуйте изменить запрос.</div>';
    return;
  }

  list.innerHTML = questions.map(q => {
    const isActive = q.id === state.selectedId;
    const scores = Object.values(q.responses || {}).map(r => r.scores?.total).filter(t => t != null);
    const qAvg = scores.length ? Math.round(avgArr(scores)) : null;

    return `
      <div class="q-item ${isActive ? 'active' : ''}" data-id="${q.id}"
           onclick="selectQuestion('${q.id}', window.BENCHMARK_RESULTS)">
        <div class="q-item-top">
          <span class="q-item-num">${q.id}</span>
          <span class="q-item-reg badge-${q.register}">${REG_SHORT[q.register] || q.register}</span>
          ${qAvg != null ? `<span class="q-item-score ${scoreClass(qAvg)}">${qAvg}</span>` : ''}
        </div>
        <div class="q-item-text">${escHtml(q.text)}</div>
      </div>`;
  }).join('');
}

function selectQuestion(qId, data) {
  state.selectedId = qId;
  state.compareMode     = false;
  state.compareSelected.clear();

  document.querySelectorAll('.q-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === qId)
  );

  const q = data.questions.find(x => x.id === qId);
  if (!q) return;

  const models  = data.models || {};
  const content = document.getElementById('contentArea');

  const sorted = Object.entries(q.responses || {}).sort(([, aR], [, bR]) => {
    const a = aR.scores?.total ?? -1;
    const b = bR.scores?.total ?? -1;
    return b - a;
  });

  const allScores = sorted.map(([, r]) => r.scores?.total).filter(t => t != null);
  const maxScore  = allScores.length ? Math.max(...allScores) : null;
  const minScore  = allScores.length ? Math.min(...allScores) : null;

  content.innerHTML = `
    <div class="q-detail">
      <div class="q-detail-header">
        <div class="q-detail-meta">
          <span class="q-detail-id">${q.id}</span>
          <span class="q-detail-reg badge-${q.register}">${REG_LABELS[q.register] || q.register}</span>
          <span class="q-diff diff-${q.difficulty}">${DIFF_LABELS[q.difficulty] || q.difficulty}</span>
        </div>
        <div class="q-detail-question">${escHtml(q.text)}</div>
        <div class="q-detail-note">
          Вопрос на узбекском языке &nbsp;·&nbsp; ${sorted.length} ответов &nbsp;·&nbsp;
          ${allScores.length ? `Лучший балл: ${maxScore} / Худший: ${minScore}` : 'Ответы ещё не оценены'}
        </div>
      </div>

      <div class="resp-toolbar">
        <div class="resp-section-label">Ответы AI-моделей — сортировка от лучшего к худшему</div>
        <button class="compare-toggle-btn" id="compareToggleBtn" onclick="toggleCompareMode()">
          Сравнить
        </button>
      </div>
      <div id="respArea"></div>
    </div>`;

  renderResponses(sorted, models, maxScore, minScore);

  content.querySelectorAll('.expand-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const textEl = btn.previousElementSibling;
      const expanded = textEl.classList.toggle('expanded');
      btn.textContent = expanded ? '▲ Свернуть' : '▼ Читать полностью';
    });
  });
}

// ── REQ-3: Compare mode ────────────────────────────────────────
function toggleCompareMode() {
  state.compareMode = !state.compareMode;
  state.compareSelected.clear();

  const btn = document.getElementById('compareToggleBtn');
  if (btn) btn.classList.toggle('active', state.compareMode);

  const data = state.appData;
  const q    = data.questions.find(x => x.id === state.selectedId);
  if (!q) return;

  const models = data.models || {};
  const sorted = Object.entries(q.responses || {}).sort(([, aR], [, bR]) => {
    const a = aR.scores?.total ?? -1;
    const b = bR.scores?.total ?? -1;
    return b - a;
  });
  const allScores = sorted.map(([, r]) => r.scores?.total).filter(t => t != null);
  const maxScore  = allScores.length ? Math.max(...allScores) : null;
  const minScore  = allScores.length ? Math.min(...allScores) : null;

  renderResponses(sorted, models, maxScore, minScore);
}

function onCompareCheck(modelId) {
  if (state.compareSelected.has(modelId)) {
    state.compareSelected.delete(modelId);
  } else {
    if (state.compareSelected.size >= 3) return;
    state.compareSelected.add(modelId);
  }

  const data = state.appData;
  const q    = data.questions.find(x => x.id === state.selectedId);
  if (!q) return;

  const models = data.models || {};
  const sorted = Object.entries(q.responses || {}).sort(([, aR], [, bR]) => {
    const a = aR.scores?.total ?? -1;
    const b = bR.scores?.total ?? -1;
    return b - a;
  });
  const allScores = sorted.map(([, r]) => r.scores?.total).filter(t => t != null);
  const maxScore  = allScores.length ? Math.max(...allScores) : null;
  const minScore  = allScores.length ? Math.min(...allScores) : null;

  renderResponses(sorted, models, maxScore, minScore);
}

function renderResponses(sorted, models, maxScore, minScore) {
  const area = document.getElementById('respArea');
  if (!area) return;

  if (!state.compareMode) {
    area.className = '';
    area.innerHTML = `
      <div class="responses-grid">
        ${sorted.map(([modelId, resp]) => renderRespCard(modelId, resp, models, maxScore, minScore, false)).join('')}
      </div>`;
  } else {
    const selected   = sorted.filter(([id]) => state.compareSelected.has(id));
    const unselected = sorted.filter(([id]) => !state.compareSelected.has(id));
    const colCount   = Math.max(2, Math.min(3, selected.length || 2));

    const selectedHtml = selected.length > 0
      ? `<div class="compare-grid compare-grid-${colCount}">
           ${selected.map(([modelId, resp]) => renderRespCard(modelId, resp, models, maxScore, minScore, true)).join('')}
         </div>`
      : '<div class="compare-hint">Выберите до 3 моделей для сравнения (установите флажок)</div>';

    const hiddenHtml = unselected.length > 0 ? `
      <div class="compare-divider">
        <span>Остальные модели (${unselected.length} скрыто)</span>
        <button class="compare-show-rest-btn" onclick="toggleRestModels(this)">Показать</button>
      </div>
      <div class="compare-rest" style="display:none">
        <div class="responses-grid">
          ${unselected.map(([modelId, resp]) => renderRespCard(modelId, resp, models, maxScore, minScore, true)).join('')}
        </div>
      </div>` : '';

    area.innerHTML = selectedHtml + hiddenHtml;
  }

  // Re-attach expand button listeners
  area.querySelectorAll('.expand-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const textEl = btn.previousElementSibling;
      const expanded = textEl.classList.toggle('expanded');
      btn.textContent = expanded ? '▲ Свернуть' : '▼ Читать полностью';
    });
  });
}

function toggleRestModels(btn) {
  const restEl = btn.closest('.compare-divider').nextElementSibling;
  if (!restEl) return;
  const isHidden = restEl.style.display === 'none';
  restEl.style.display = isHidden ? 'block' : 'none';
  btn.textContent = isHidden ? 'Скрыть' : 'Показать';
}

function renderRespCard(modelId, resp, modelsMeta, maxScore, minScore, compareMode) {
  const meta   = modelsMeta[modelId] || getModelMeta(modelId, state.appData || {});
  const scores = resp.scores;
  const total  = scores?.total;

  let cardClass = 'resp-card';
  if (total != null && maxScore != null && minScore != null && maxScore !== minScore) {
    if (total === maxScore) cardClass += ' resp-card-best';
    else if (total === minScore) cardClass += ' resp-card-worst';
  }

  // REQ-3: checkbox for compare mode
  const checkboxHtml = compareMode ? (() => {
    const isChecked  = state.compareSelected.has(modelId);
    const isDisabled = !isChecked && state.compareSelected.size >= 3;
    return `<input type="checkbox" class="compare-check" ${isChecked ? 'checked' : ''} ${isDisabled ? 'disabled' : ''}
              onchange="onCompareCheck('${modelId}')" title="Выбрать для сравнения" />`;
  })() : '';

  const scoreBadge = total != null ? `
    <div class="resp-score-box">
      <div class="resp-score-num ${scoreClass(total)}">${Math.round(total)}</div>
      <div class="resp-score-sub">из 100</div>
    </div>` : '';

  let dims = '';
  if (scores && (scores.D1 || scores.D2 || scores.D3 || scores.D4)) {
    dims = `
      <div class="resp-dims">
        ${['D1','D2','D3','D4'].map(d => {
          const val  = scores[d];
          const info = DIM_INFO[d];
          return `
            <div class="resp-dim" data-tooltip="${escHtml(info.tooltip)}">
              <div class="resp-dim-label">${info.name}<span class="dim-help">?</span></div>
              <div class="resp-dim-stars">${dimStars(val)}</div>
              <div class="resp-dim-val">${val} / 5</div>
            </div>`;
        }).join('')}
      </div>`;
  }

  let body = '';
  if (resp.error) {
    body = `<div class="resp-error">Ошибка: ${escHtml(resp.error)}</div>`;
  } else if (resp.response) {
    const text   = resp.response;
    const isLong = text.length > 500;
    body = `
      <div class="resp-text">${escHtml(text)}</div>
      ${isLong ? '<button class="expand-btn">▼ Читать полностью</button>' : ''}
      ${dims}`;
  } else {
    body = '<div class="resp-error">Ответ отсутствует</div>';
  }

  const latency = resp.latency_ms ? `⏱ ${resp.latency_ms.toLocaleString()} мс` : '';
  const comment = scores?.izoh ? `«${escHtml(scores.izoh)}»` : '';

  return `
    <div class="${cardClass}">
      <div class="resp-header">
        <div class="resp-header-row">
          <div class="resp-model-info">
            ${checkboxHtml}
            <div class="resp-model-dot" style="background:${meta.color}"></div>
            <div>
              <div class="resp-model-name">${escHtml(meta.name)}</div>
              <div class="resp-model-sub">
                ${escHtml(meta.provider || '')}
                <span class="type-badge type-${meta.type}">
                  ${meta.type === 'commercial' ? 'Коммерческая' : 'Open-Source'}
                </span>
              </div>
            </div>
          </div>
          ${scoreBadge}
        </div>
      </div>
      <div class="resp-body">${body}</div>
      ${(latency || comment) ? `
        <div class="resp-footer">
          <span class="resp-latency">${latency}</span>
          <span class="resp-judge" title="${escHtml(scores?.izoh || '')}">${comment}</span>
        </div>` : ''}
    </div>`;
}

function dimStars(val) {
  if (!val) return '–';
  return `<span class="stars-filled">${'★'.repeat(val)}</span><span class="stars-empty">${'☆'.repeat(5 - val)}</span>`;
}

// ═══════════════════════════════════════════════════════════════
// ВСПЛЫВАЮЩИЕ ПОДСКАЗКИ
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
// УТИЛИТЫ
// ═══════════════════════════════════════════════════════════════

function scoreClass(val) {
  if (!val && val !== 0) return 'score-red';
  return val >= 80 ? 'score-green' : val >= 60 ? 'score-yellow' : 'score-red';
}

function avgArr(arr) {
  if (!arr || !arr.length) return 0;
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
