from pathlib import Path


def test_index_template_uses_reader_design_and_functional_ids():
    template = Path("templates/index.html").read_text(encoding="utf-8")
    style = Path("static/style.css").read_text(encoding="utf-8")

    assert "reader-shell" in template
    assert "feed-sidebar" in template
    assert "article-column" in template
    assert "research-panel" in template
    assert 'id="search-form"' in template
    assert 'id="search-input"' in template
    assert '<details id="live-answer-box"' in template
    assert '<details id="sources-box"' in template
    assert 'id="refresh-button"' in template
    assert 'id="theme-toggle-button"' in template
    assert "rss-analyzer-theme" in template
    assert "{{ top_label }}" in template
    assert "{{ top_metric_label }}" in template
    assert ".brand-actions" in style
    assert "flex: 0 0 38px" in style
    assert "calc(100% - 92px)" in style
    assert ".article-toolbar::before" in style
    assert "background: var(--brand-bg)" in style
    assert '.feed-pill' in style
    assert 'font-family: "Inter", ui-sans-serif, system-ui, sans-serif' in style
    assert "font-style: normal" in style
    assert '.search-form input[type="text"]::placeholder' in style
    assert "font-weight: 500" in style
    assert ".result-panel summary" in style
    assert 'content: "Einklappen"' in style
