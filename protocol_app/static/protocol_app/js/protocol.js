/* ═══════════════════════════════════════════════════════════════════════════
   PROTOCOL OS — Master JavaScript Engine
   Modules: Liquid Bars · Calendar · Day Card · Modal · Processing
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ══════════════════════════════════════════════════════════════════════════
   1. LIQUID BAR ANIMATIONS
   ══════════════════════════════════════════════════════════════════════════ */

/**
 * Animates a single bar fill element from 0 to its data-target percentage.
 * Uses a cubic ease-out curve for the "liquid fill" physics feel.
 * @param {HTMLElement} el  - The fill div
 * @param {number}      pct - Target percentage (0–100)
 * @param {number}      delay - Start delay in ms
 */
function animateBar(el, pct, delay = 0) {
  if (!el) return;
  const duration   = 1400;
  const startTime  = performance.now() + delay;

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function tick(now) {
    if (now < startTime) {
      requestAnimationFrame(tick);
      return;
    }
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = easeOutCubic(progress);
    el.style.width = (eased * pct) + '%';

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
}

/**
 * Reads all [data-target] bar elements on the page and animates them.
 * Called once on DOMContentLoaded.
 */
function initAllBars() {
  // Score bar (0–10 scale mapped to 0–100%)
  const scoreFill = document.getElementById('scoreFill');
  if (scoreFill) {
    const target  = parseFloat(scoreFill.dataset.target || 0);
    const max     = parseFloat(scoreFill.dataset.max || 22.75);
    const pct     = (target / max) * 100;
    animateBar(scoreFill, pct, 300);
  }

  // Rank progress fill (toward next rank)
  const rankProgressFill = document.getElementById('rankProgressFill');
  if (rankProgressFill) {
    const target = parseFloat(rankProgressFill.dataset.target || 0);
    animateBar(rankProgressFill, target, 600);
  }

  // Mini stat bars (already in % from the template)
  const miniBarIds = ['barIT', 'barBooks', 'barKcal', 'barKm'];
  miniBarIds.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (el) {
      const target = parseFloat(el.dataset.target || 0);
      animateBar(el, target, 400 + idx * 120);
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   2. MODAL CONTROLLER
   ══════════════════════════════════════════════════════════════════════════ */

const modalBg = () => document.getElementById('reportModalBg');

function openModal() {
  const bg = modalBg();
  if (!bg) return;
  bg.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const bg = modalBg();
  if (!bg) return;
  bg.classList.remove('open');
  document.body.style.overflow = '';
}

/**
 * Closes the modal only if the user clicked the dark backdrop,
 * not the modal card itself.
 */
function handleModalBgClick(e) {
  if (e.target === modalBg()) {
    closeModal();
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   3. PROCESSING OVERLAY
   ══════════════════════════════════════════════════════════════════════════ */

function showProcessing() {
  const overlay = document.getElementById('processingOverlay');
  if (overlay) overlay.classList.add('active');
}

/**
 * Intercepts the modal form submission:
 * 1. Shows the "Processing Data..." overlay.
 * 2. Lets the form POST normally after a brief dramatic pause.
 */
function handleFormSubmit(e) {
  // Don't preventDefault — we want the real POST to go through.
  // Just show the overlay immediately for effect.
  showProcessing();
  // The form will submit and redirect naturally.
}

/* ══════════════════════════════════════════════════════════════════════════
   4. CALENDAR ENGINE
   ══════════════════════════════════════════════════════════════════════════ */

const CalState = {
  year:  null,
  month: null,
  open:  false,
};

/**
 * Opens the full-screen calendar overlay.
 * Optionally auto-opens the day card for a specific date.
 * @param {string|null} autoOpenDate  - 'YYYY-MM-DD' or null
 */
function openCalendar(autoOpenDate = null) {
  const overlay = document.getElementById('calendarOverlay');
  if (!overlay) return;

  // Init to current month if not set
  if (!CalState.year) {
    const today = new Date(TODAY_DATE);
    CalState.year  = today.getFullYear();
    CalState.month = today.getMonth() + 1; // 1-indexed
  }

  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  CalState.open = true;

  fetchCalendarMonth(CalState.year, CalState.month, autoOpenDate);
}

function closeCalendar() {
  const overlay = document.getElementById('calendarOverlay');
  if (overlay) overlay.classList.remove('open');
  document.body.style.overflow = '';
  CalState.open = false;
  closeDayCard();
}

/**
 * Navigate calendar forward/backward by one month.
 * @param {number} dir  +1 or -1
 */
function calNavigate(dir) {
  CalState.month += dir;

  if (CalState.month > 12) {
    CalState.month = 1;
    CalState.year += 1;
  } else if (CalState.month < 1) {
    CalState.month = 12;
    CalState.year -= 1;
  }

  fetchCalendarMonth(CalState.year, CalState.month);
}

/**
 * Fetches heatmap data from the AJAX endpoint and renders the grid.
 * @param {number}      year
 * @param {number}      month
 * @param {string|null} autoOpenDate
 */
function fetchCalendarMonth(year, month, autoOpenDate = null) {
  const grid      = document.getElementById('calGrid');
  const titleEl   = document.getElementById('calMonthTitle');

  // Loading state
  if (grid) {
    grid.innerHTML = `
      <div style="
        grid-column: 1 / 8;
        text-align: center;
        padding: 48px 0;
        color: var(--text-dim);
        font-family: var(--font-head);
        font-size: 10px;
        letter-spacing: 3px;
      ">LOADING...</div>
    `;
  }

  const url = `/ajax/calendar/?year=${year}&month=${month}`;

  fetch(url, {
    method: 'GET',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'same-origin',
  })
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(data => {
    CalState.year  = data.year;
    CalState.month = data.month;

    if (titleEl) {
      titleEl.textContent = `${data.month_name} ${data.year}`;
    }

    renderCalGrid(data, autoOpenDate);
  })
  .catch(err => {
    console.error('Calendar fetch failed:', err);
    if (grid) {
      grid.innerHTML = `
        <div style="
          grid-column:1/8;
          text-align:center;
          padding:48px 0;
          color:#cc2200;
          font-size:12px;
        ">Failed to load calendar. Please refresh.</div>
      `;
    }
  });
}

/**
 * Renders the calendar grid from AJAX data.
 * @param {Object}      data          - API response
 * @param {string|null} autoOpenDate  - date to auto-open day card for
 */
function renderCalGrid(data, autoOpenDate = null) {
  const grid = document.getElementById('calGrid');
  if (!grid) return;

  const { days, first_weekday } = data;
  let html = '';

  // Empty padding cells before the 1st
  // first_weekday: 0=Mon, 6=Sun
  for (let i = 0; i < first_weekday; i++) {
    html += `<div class="cal-day-cell empty-cell"></div>`;
  }

  days.forEach(day => {
    const isFuture  = day.is_future;
    const isEmpty   = day.dot_class === 'dot-empty';
    const classes   = [
      'cal-day-cell',
      day.is_today  ? 'is-today'  : '',
      isFuture      ? 'is-future' : '',
    ].filter(Boolean).join(' ');

    const dotHtml = `<div class="heat-dot ${day.dot_class}"></div>`;

    const clickHandler = (!isFuture)
      ? `onclick="openDayCard('${day.date}')" `
      : '';

    html += `
      <div class="${classes}" ${clickHandler} title="${day.date}">
        <span class="cal-day-number">${day.day}</span>
        ${dotHtml}
      </div>
    `;
  });

  grid.innerHTML = html;

  // Auto-open a specific day card if requested
  if (autoOpenDate) {
    setTimeout(() => openDayCard(autoOpenDate), 200);
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   5. DAY CARD (AJAX Panel)
   ══════════════════════════════════════════════════════════════════════════ */

function openDayCard(dateStr) {
  const panel = document.getElementById('dayCardPanel');
  if (!panel) return;

  // Show panel immediately with loading state
  panel.classList.add('open');
  document.getElementById('dayCardContent').innerHTML = `
    <div style="
      text-align:center;
      padding: 32px 0;
      color: var(--text-dim);
      font-family: var(--font-head);
      font-size: 10px;
      letter-spacing: 3px;
    ">
      <div class="processing-spinner" style="margin: 0 auto 16px;"></div>
      LOADING DATA...
    </div>
  `;

  // Fetch day data
  fetch(`/ajax/day/${dateStr}/`, {
    method: 'GET',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'same-origin',
  })
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(data => renderDayCard(data))
  .catch(err => {
    console.error('Day card fetch failed:', err);
    document.getElementById('dayCardContent').innerHTML = `
      <p style="color:#cc2200;text-align:center;padding:24px 0;font-size:13px;">
        Failed to load day data.
      </p>
    `;
  });
}

function closeDayCard() {
  const panel = document.getElementById('dayCardPanel');
  if (panel) panel.classList.remove('open');
}

/**
 * Renders the day card HTML from AJAX data and animates its mini-bars.
 * @param {Object} data  - DayCardAjaxView JSON response
 */
/* PATH: Day Card — renderDayCard (Bug 1 Fix: raw HTML rendering) */
function renderDayCard(data) {
  const content = document.getElementById('dayCardContent');
  if (!content) return;

  if (!data.exists) {
    // Build DOM elements manually — never use innerHTML with href strings
    content.innerHTML = '';

    const dateEl = document.createElement('div');
    dateEl.className = 'day-card-date';
    dateEl.textContent = data.date_display;
    content.appendChild(dateEl);

    const emptyWrap = document.createElement('div');
    emptyWrap.className = 'day-card-empty';

    const msg = document.createElement('p');
    msg.textContent = 'No data logged for this day.';
    emptyWrap.appendChild(msg);

    // Create the button as a real anchor element
    const logBtn = document.createElement('a');
    logBtn.href    = '/report/add/' + data.date + '/';
    logBtn.className = 'protocol-submit-btn';
    logBtn.style.cssText = 'display:block;text-align:center;padding:14px;';
    logBtn.textContent = 'LOG THIS DAY';
    emptyWrap.appendChild(logBtn);

    content.appendChild(emptyWrap);
    return;
  }

  // Score color
  let scoreColor = '#cc2200';
  if (data.score >= 7.5) scoreColor = '#bfa020';
  else if (data.score >= 4) scoreColor = '#00bcd4';

  // Build main content via innerHTML (safe — all values are numbers/text from our own API)
  content.innerHTML = `
    <div class="day-card-date">${escapeHtml(data.date_display)}</div>

    <div class="day-card-score-row">
      <span style="
        font-family: var(--font-head);
        font-size: 52px;
        font-weight: 900;
        line-height: 1;
        color: ${scoreColor};
      ">${parseFloat(data.score).toFixed(2)}</span>
      <div>
        <div class="day-card-rank">${escapeHtml(data.rank)}</div>
      </div>
    </div>

    <p class="day-card-ai-comment">${escapeHtml(data.ai_comment)}</p>

    <div class="day-card-stats">

      <div class="stat-row">
        <div class="stat-info">
          <div class="stat-header">
            <span class="stat-name">IT / MATH</span>
            <span class="stat-value">${data.it_hours}h <span class="stat-target">/ 1h</span></span>
          </div>
          <div class="mini-bar-track">
            <div class="mini-bar-fill it" id="dc-barIT"
              style="width:0%" data-target="${data.it_pct}"></div>
          </div>
        </div>
      </div>

      <div class="stat-row">
        <div class="stat-info">
          <div class="stat-header">
            <span class="stat-name">BOOKS</span>
            <span class="stat-value">${data.pages}pp <span class="stat-target">/ 50pp</span></span>
          </div>
          <div class="mini-bar-track">
            <div class="mini-bar-fill books" id="dc-barBooks"
              style="width:0%" data-target="${data.books_pct}"></div>
          </div>
        </div>
      </div>

      <div class="stat-row">
        <div class="stat-info">
          <div class="stat-header">
            <span class="stat-name">KCAL</span>
            <span class="stat-value">${data.calories} <span class="stat-target">/ 500</span></span>
          </div>
          <div class="mini-bar-track">
            <div class="mini-bar-fill kcal" id="dc-barKcal"
              style="width:0%" data-target="${data.kcal_pct}"></div>
          </div>
        </div>
      </div>

      <div class="stat-row">
        <div class="stat-info">
          <div class="stat-header">
            <span class="stat-name">DISTANCE</span>
            <span class="stat-value">${data.distance_km}km <span class="stat-target">/ 5km</span></span>
          </div>
          <div class="mini-bar-track">
            <div class="mini-bar-fill km" id="dc-barKm"
              style="width:0%" data-target="${data.km_pct}"></div>
          </div>
        </div>
      </div>

    </div>
  `;

  // Bug 3 Fix — "EDIT THIS DAY" button built as real DOM element
  /* PATH: Bug 3 Fix — Edit Logged Day Button */
  /* PATH: Day Card Actions — Edit + Delete buttons */
  const actionsWrap = document.createElement('div');
  actionsWrap.style.cssText = 'margin-top:20px;display:flex;gap:8px;';

  const editBtn = document.createElement('a');
  editBtn.href = '/report/add/' + data.date + '/';
  editBtn.className = 'protocol-submit-btn';
  editBtn.style.cssText = 'display:flex;align-items:center;justify-content:center;padding:14px;flex:1;text-decoration:none;';
  editBtn.textContent = 'EDIT THIS DAY';
  actionsWrap.appendChild(editBtn);

  // Delete button — links to confirmation page
  const delBtn = document.createElement('a');
  delBtn.href = '/report/delete/' + data.date + '/';
  delBtn.style.cssText = `
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 14px 16px;
    background: var(--low-bg);
    border: 1px solid rgba(192,57,43,0.2);
    border-radius: var(--r-lg);
    color: var(--low-color);
    font-family: var(--font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    text-decoration: none;
    flex-shrink: 0;
    transition: all 0.2s ease;
  `;
  delBtn.textContent = 'DEL';
  delBtn.onmouseover = () => { delBtn.style.background = '#C0392B'; delBtn.style.color = '#fff'; };
  delBtn.onmouseout  = () => { delBtn.style.background = 'var(--low-bg)'; delBtn.style.color = 'var(--low-color)'; };
  actionsWrap.appendChild(delBtn);

  content.appendChild(actionsWrap);

  // Animate the day card mini bars
  const dcBars = [
    { id: 'dc-barIT',    delay: 100 },
    { id: 'dc-barBooks', delay: 200 },
    { id: 'dc-barKcal',  delay: 300 },
    { id: 'dc-barKm',    delay: 400 },
  ];
  dcBars.forEach(({ id, delay }) => {
    const el = document.getElementById(id);
    if (el) animateBar(el, parseFloat(el.dataset.target || 0), delay);
  });
}

/* PATH: Security — HTML escape helper (prevents XSS in JS-rendered content) */
function escapeHtml(str) {
  if (typeof str !== 'string') return String(str);
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/* ══════════════════════════════════════════════════════════════════════════
   6. KEYBOARD NAVIGATION
   ══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    // Priority: day card → calendar → modal
    const panel   = document.getElementById('dayCardPanel');
    const cal     = document.getElementById('calendarOverlay');
    const modalBg = document.getElementById('reportModalBg');

    if (panel && panel.classList.contains('open')) {
      closeDayCard();
    } else if (cal && cal.classList.contains('open')) {
      closeCalendar();
    } else if (modalBg && modalBg.classList.contains('open')) {
      closeModal();
    }
  }

  // Calendar arrow navigation
  if (CalState.open) {
    if (e.key === 'ArrowLeft')  calNavigate(-1);
    if (e.key === 'ArrowRight') calNavigate(1);
  }
});

/* ══════════════════════════════════════════════════════════════════════════
   7. SWIPE TO CLOSE (Mobile)
   ══════════════════════════════════════════════════════════════════════════ */

(function initSwipeToClose() {
  let touchStartY = 0;
  const SWIPE_THRESHOLD = 80; // px

  function addSwipeClose(elId, closeFn) {
    const el = document.getElementById(elId);
    if (!el) return;

    el.addEventListener('touchstart', e => {
      touchStartY = e.touches[0].clientY;
    }, { passive: true });

    el.addEventListener('touchend', e => {
      const dy = e.changedTouches[0].clientY - touchStartY;
      if (dy > SWIPE_THRESHOLD) {
        closeFn();
      }
    }, { passive: true });
  }

  addSwipeClose('dayCardPanel',  closeDayCard);
  addSwipeClose('protocol-modal', closeModal);
})();

/* ══════════════════════════════════════════════════════════════════════════
   8. RANK GLOW EFFECT (Dynamic color on rank icon)
   ══════════════════════════════════════════════════════════════════════════ */

function initRankGlow() {
  const rankCard = document.querySelector('.rank-bar');
  if (!rankCard) return;

  const scoreClass = rankCard.classList;
  let glowColor = 'rgba(139,0,0,0.15)';

  if (scoreClass.contains('score-high')) {
    glowColor = 'rgba(191,160,32,0.2)';
  } else if (scoreClass.contains('score-mid')) {
    glowColor = 'rgba(0,188,212,0.15)';
  }

  rankCard.style.boxShadow = `inset 0 0 60px ${glowColor}`;
}

/* ══════════════════════════════════════════════════════════════════════════
   9. QUOTE CARD FADE-IN ON LOAD
   ══════════════════════════════════════════════════════════════════════════ */

function initQuoteFade() {
  const quote = document.querySelector('.quote-card');
  if (!quote) return;

  quote.style.opacity = '0';
  quote.style.transform = 'translateY(12px)';
  quote.style.transition = 'opacity 0.8s ease, transform 0.8s ease';

  setTimeout(() => {
    quote.style.opacity  = '1';
    quote.style.transform = 'translateY(0)';
  }, 200);
}

/* ══════════════════════════════════════════════════════════════════════════
   10. STAGGERED CARD ENTRANCE
   ══════════════════════════════════════════════════════════════════════════ */

function initCardEntrance() {
  const cards = document.querySelectorAll('.protocol-card, .shadow-card');
  cards.forEach((card, i) => {
    card.style.opacity   = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = `opacity 0.6s ease ${i * 80}ms, transform 0.6s ease ${i * 80}ms`;

    // Use IntersectionObserver for scroll-triggered reveal
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity   = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    observer.observe(card);
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   11. WEEK DOT HOVER SCORES (tooltip-style)
   ══════════════════════════════════════════════════════════════════════════ */

function initWeekDotTooltips() {
  const cells = document.querySelectorAll('.week-day-cell');
  cells.forEach(cell => {
    const dot = cell.querySelector('.heat-dot');
    if (!dot) return;

    // Tiny score label on hover
    cell.addEventListener('mouseenter', () => {
      const date = cell.getAttribute('title');
      if (date) {
        cell.setAttribute('data-tip', date);
      }
    });
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   12. CSRF TOKEN HELPER (for future AJAX POST calls)
   ══════════════════════════════════════════════════════════════════════════ */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const CSRF_TOKEN = getCookie('csrftoken');

/* ══════════════════════════════════════════════════════════════════════════
   13. PROTOCOL HEADLINE TYPEWRITER EFFECT (optional, hero only)
   ══════════════════════════════════════════════════════════════════════════ */

function initHeadlineEffect() {
  const headline = document.querySelector('.hero-headline');
  if (!headline) return;

  // Just ensure it fades in cleanly
  headline.style.opacity   = '0';
  headline.style.transition = 'opacity 1s ease';

  setTimeout(() => {
    headline.style.opacity = '1';
  }, 50);
}

/* ══════════════════════════════════════════════════════════════════════════
   14. BOOT SEQUENCE — DOMContentLoaded
   ══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

  // Core animations
  initAllBars();
  initRankGlow();
  initQuoteFade();
  initCardEntrance();
  initWeekDotTooltips();
  initHeadlineEffect();

  // Close processing overlay if we navigated back to a page
  // (browser back button after form submit)
  const overlay = document.getElementById('processingOverlay');
  if (overlay && overlay.classList.contains('active')) {
    overlay.classList.remove('active');
  }

  // If modal was left open (e.g. form validation error reload),
  // re-open it automatically
  const modalBgEl = document.getElementById('reportModalBg');
  if (modalBgEl && modalBgEl.dataset.forceOpen === 'true') {
    openModal();
  }

  // Expose globals for inline onclick handlers
  window.openModal       = openModal;
  window.closeModal      = closeModal;
  window.handleModalBgClick = handleModalBgClick;
  window.handleFormSubmit   = handleFormSubmit;
  window.showProcessing     = showProcessing;
  window.openCalendar    = openCalendar;
  window.closeCalendar   = closeCalendar;
  window.calNavigate     = calNavigate;
  window.openDayCard     = openDayCard;
  window.closeDayCard    = closeDayCard;

  console.log('%cPROTOCOL OS — ONLINE', [
    'color: #bfa020',
    'font-size: 14px',
    'font-weight: bold',
    'font-family: monospace',
    'letter-spacing: 4px',
    'padding: 8px 0',
  ].join(';'));
});