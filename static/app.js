// static/app.js

// -> Helper: versucht erst ID, dann Klasse
function _get(selector) {
  return document.getElementById(selector) || document.querySelector(`.${selector}`);
}

// Spinner anzeigen/verstecken
function showSpinner() {
  const spinner = _get('spinner');
  if (spinner) spinner.style.display = 'inline-block';
}
function hideSpinner() {
  const spinner = _get('spinner');
  if (spinner) spinner.style.display = 'none';
}

// Section anzeigen/verstecken/leeren
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

// Haupt-Handler für AJAX-Suche
async function handleSearch(event) {
  event.preventDefault();

  const form    = _get('search-form');
  const inputEl = _get('search-input') || (form && form.querySelector('input[name="question"]'));
  if (!form || !inputEl) {
    console.error('Suchformular oder Eingabefeld nicht gefunden!');
    return;
  }

  const question = inputEl.value.trim();
  if (!question) {
    console.warn('Leere Frage – nichts zu tun.');
    return;
  }

  // Alte Ausgabe zurücksetzen
  clearSection('live-answer-box');
  clearSection('sources-box');
  hideSection('live-answer-box');
  hideSection('sources-box');
  showSpinner();

  console.debug('Sende Frage an /search:', question);
  try {
    const res = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    // erst hier Spinner verstecken, wenn HTTP-Call durch ist
    hideSpinner();

    if (!res.ok) {
      console.error('API-Antwort war kein OK, Form-Submit als Fallback');
      form.submit();
      return;
    }

    const data = await res.json();
    console.debug('Antwort von API erhalten:', data);

    // Antwort-Box
    const ansBox = _get('live-answer-box');
    if (ansBox) {
      ansBox.innerHTML = `
        <h2>Antwort</h2>
        <div class="answer-content">${data.answer}</div>
      `;
      showSection('live-answer-box');
    } else {
      console.warn('live-answer-box nicht gefunden');
    }

    // Quellen-Box
    const srcBox = _get('sources-box');
    if (srcBox) {
      if (Array.isArray(data.sources) && data.sources.length) {
        let html = '<h3>Quellen</h3><ol>';
        data.sources.forEach(s => {
          html += `<li>
                     <a href="${s.link}" target="_blank" rel="noopener">
                       ${s.title}
                     </a>
                   </li>`;
        });
        html += '</ol>';
        srcBox.innerHTML = html;
        showSection('sources-box');
      } else {
        console.debug('Keine Quellen zurückgegeben.');
      }
    } else {
      console.warn('sources-box nicht gefunden');
    }

  } catch (err) {
    hideSpinner();
    console.error('AJAX-Fehler, klassisches Submit', err);
    form.submit();
  }
}

// Setup nach DOM-Ready
document.addEventListener('DOMContentLoaded', () => {
  const form = _get('search-form');
  if (form) {
    form.addEventListener('submit', handleSearch);
  } else {
    console.error('search-form nicht gefunden!');
  }

  // Sicherstellen, dass nur ein <details> offen ist
  document.querySelectorAll('details.article').forEach(det => {
    det.addEventListener('toggle', () => {
      if (det.open) {
        document
          .querySelectorAll('details.article[open]')
          .forEach(o => { if (o !== det) o.open = false; });
      }
    });
  });
});
