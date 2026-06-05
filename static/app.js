// static/app.js

function _get(selector) {
  return document.getElementById(selector) || document.querySelector(`.${selector}`);
}

function showSpinner() {
  const spinner = _get('spinner');
  if (spinner) spinner.style.display = 'inline-block';
}

function hideSpinner() {
  const spinner = _get('spinner');
  if (spinner) spinner.style.display = 'none';
}

function showSection(id) {
  const sec = _get(id);
  if (sec) sec.style.display = 'block';
}

function hideSection(id) {
  const sec = _get(id);
  if (sec) sec.style.display = 'none';
}

function clearSection(id) {
  const sec = _get(id);
  if (sec) sec.innerHTML = '';
}

function escapeHTML(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderInlineMarkdown(value) {
  return escapeHTML(value)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_match, label, url) => {
      return `<a href="${escapeHTML(url)}" target="_blank" rel="noopener">${label}</a>`;
    });
}

function renderMarkdownAnswer(value) {
  const lines = String(value || '').replace(/\r\n/g, '\n').split('\n');
  const html = [];
  let listOpen = false;
  let paragraph = [];

  function closeList() {
    if (listOpen) {
      html.push('</ul>');
      listOpen = false;
    }
  }

  function flushParagraph() {
    if (paragraph.length) {
      html.push(`<p>${paragraph.map(renderInlineMarkdown).join(' ')}</p>`);
      paragraph = [];
    }
  }

  lines.forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      closeList();
      return;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      closeList();
      const level = heading[1].length === 1 ? 3 : Math.min(heading[1].length + 1, 4);
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      return;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      if (!listOpen) {
        html.push('<ul>');
        listOpen = true;
      }
      html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
      return;
    }

    paragraph.push(trimmed);
  });

  flushParagraph();
  closeList();
  return html.join('');
}

function sourceLabel(source) {
  if (source.source_type === 'official') return 'Offiziell';
  if (source.is_speculative || source.source_type === 'speculative' || source.source_type === 'community') {
    return 'Unbestaetigt';
  }
  if (source.source_type === 'third_party') return 'Drittquelle';
  return 'Quelle';
}

function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

function setTheme(theme) {
  const normalized = theme === 'dark' ? 'dark' : 'light';
  if (normalized === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }

  try {
    localStorage.setItem('rss-analyzer-theme', normalized);
  } catch (_err) {}

  const button = _get('theme-toggle-button');
  if (button) {
    const isDark = normalized === 'dark';
    button.setAttribute('aria-pressed', String(isDark));
    button.setAttribute('title', isDark ? 'Light Theme aktivieren' : 'Dark Theme aktivieren');
    button.setAttribute('data-mode', normalized);
    const icon = button.querySelector('.theme-icon');
    if (icon) icon.textContent = isDark ? '☀' : '◐';
  }
}

function initTheme() {
  let stored = 'light';
  try {
    stored = localStorage.getItem('rss-analyzer-theme') || currentTheme();
  } catch (_err) {
    stored = currentTheme();
  }
  setTheme(stored === 'dark' ? 'dark' : 'light');
}

function handleThemeToggle() {
  setTheme(currentTheme() === 'dark' ? 'light' : 'dark');
}

async function handleRefresh() {
  const button = _get('refresh-button');
  if (button) {
    button.disabled = true;
    button.classList.add('loading');
  }
  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    if (!res.ok) throw new Error(`Refresh failed: ${res.status}`);
    window.location.reload();
  } catch (err) {
    console.error('Refresh fehlgeschlagen', err);
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove('loading');
    }
  }
}

async function handleSearch(event) {
  event.preventDefault();

  const form = _get('search-form');
  const inputEl = _get('search-input') || (form && form.querySelector('input[name="question"]'));
  if (!form || !inputEl) {
    console.error('Suchformular oder Eingabefeld nicht gefunden.');
    return;
  }

  const question = inputEl.value.trim();
  if (!question) {
    console.warn('Leere Frage - nichts zu tun.');
    return;
  }

  clearSection('live-answer-box');
  clearSection('sources-box');
  hideSection('live-answer-box');
  hideSection('sources-box');
  hideSection('research-empty');
  showSpinner();

  try {
    const res = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    hideSpinner();

    if (!res.ok) {
      console.error('API-Antwort war kein OK, Form-Submit als Fallback.');
      form.submit();
      return;
    }

    const data = await res.json();

    const ansBox = _get('live-answer-box');
    if (ansBox) {
      ansBox.innerHTML = `
        <summary><span>Antwort</span></summary>
        <div class="answer-content">${renderMarkdownAnswer(data.answer)}</div>
      `;
      ansBox.open = true;
      showSection('live-answer-box');
    }

    const srcBox = _get('sources-box');
    if (srcBox && Array.isArray(data.sources) && data.sources.length) {
      let html = '<summary><span>Quellen</span></summary><ol>';
      data.sources.forEach(source => {
        const link = source.link || source.url || '';
        const score = typeof source.credibility_score === 'number'
          ? ` - Vertrauen ${Math.round(source.credibility_score * 100)}%`
          : '';
        html += `<li>
          <a href="${escapeHTML(link)}" target="_blank" rel="noopener">${escapeHTML(source.title)}</a>
          <div class="source-meta">${escapeHTML(sourceLabel(source))}${escapeHTML(score)}</div>
          ${source.snippet ? `<div class="source-snippet">${escapeHTML(source.snippet)}</div>` : ''}
        </li>`;
      });
      html += '</ol>';
      srcBox.innerHTML = html;
      srcBox.open = true;
      showSection('sources-box');
    }
  } catch (err) {
    hideSpinner();
    console.error('AJAX-Fehler, klassisches Submit.', err);
    form.submit();
  }
}

window.renderMarkdownAnswer = renderMarkdownAnswer;
window.sourceLabel = sourceLabel;
window.handleSearch = handleSearch;
window.handleRefresh = handleRefresh;
window.handleThemeToggle = handleThemeToggle;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();

  const form = _get('search-form');
  if (form) {
    form.addEventListener('submit', handleSearch);
  }

  const refreshButton = _get('refresh-button');
  if (refreshButton) {
    refreshButton.addEventListener('click', handleRefresh);
  }

  const themeButton = _get('theme-toggle-button');
  if (themeButton) {
    themeButton.addEventListener('click', handleThemeToggle);
  }

  document.querySelectorAll('details.article').forEach(det => {
    det.addEventListener('toggle', () => {
      if (det.open) {
        document
          .querySelectorAll('details.article[open]')
          .forEach(openDetail => {
            if (openDetail !== det) openDetail.open = false;
          });
      }
    });
  });
});
