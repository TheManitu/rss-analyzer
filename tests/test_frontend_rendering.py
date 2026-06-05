from pathlib import Path


def test_search_ui_renders_markdown_answer_and_source_metadata():
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert "renderMarkdownAnswer(data.answer)" in app_js
    assert "renderText(data.answer)" not in app_js
    assert "source-snippet" in app_js
    assert "sourceLabel(source)" in app_js
    assert "<summary><span>Antwort</span></summary>" in app_js
    assert "<summary><span>Quellen</span></summary><ol>" in app_js
    assert "ansBox.open = true" in app_js
    assert "srcBox.open = true" in app_js
    assert "window.handleSearch = handleSearch" in app_js
    assert "window.handleRefresh = handleRefresh" in app_js
    assert "window.handleThemeToggle = handleThemeToggle" in app_js
    assert "rss-analyzer-theme" in app_js
