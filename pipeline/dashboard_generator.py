import pandas as pd
from storage.duckdb_storage import DuckDBStorage

class DashboardGenerator:
    def __init__(self, db_path=None, output_path="dashboard.html"):
        self.storage = DuckDBStorage(db_path=db_path)
        self.output = output_path

    def run(self, article_limit: int = 25):
        # 1) Top-Artikel laden
        articles = self.storage.get_all_articles()
        df_articles = pd.DataFrame(articles).head(article_limit)

        # Keywords pro Artikel
        df_articles['keywords'] = df_articles['link'].apply(
            lambda l: ", ".join(self.storage.get_article_keywords(l))
        )

        # 2) Keyword-Statistiken: Häufigkeit + Quellen
        kw_map = {}
        for link in self.storage.get_all_links():
            kws = self.storage.get_article_keywords(link)
            for kw in kws:
                kw_map.setdefault(kw, []).append(link)

        kw_rows = []
        for kw, links in kw_map.items():
            # Quellen als klickbare Links
            sources = ", ".join(
                f"<a href='{l}' target='_blank'>{l}</a>"
                for l in links
            )
            kw_rows.append({
                "keyword":   kw,
                "frequency": len(links),
                "sources":   sources
            })

        df_keywords = (
            pd.DataFrame(kw_rows)
              .sort_values("frequency", ascending=False)
              .reset_index(drop=True)
        )

        # 3) HTML-Tabellen erzeugen
        html_articles = df_articles[[
            "title", "topic", "importance", "keywords", "summary"
        ]].to_html(
            index=False,
            classes="table table-striped",
            border=0,
            escape=False
        )

        html_keywords = df_keywords[[
            "keyword", "frequency", "sources"
        ]].to_html(
            index=False,
            classes="table table-striped",
            border=0,
            escape=False
        )

        # 4) komplettes HTML-Gerüst
        html = f"""<!DOCTYPE html>
<html lang='de'>
<head>
  <meta charset='UTF-8'>
  <title>RSS Analyzer Dashboard</title>
  <link rel="stylesheet"
        href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="p-4">
  <h1>Artikel-Dashboard</h1>
  <h2>Top {article_limit} Artikel</h2>
  <table id="art-table">{html_articles}</table>

  <h2>Keyword-Analyse</h2>
  <table id="kw-table">{html_keywords}</table>

  <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
  <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
  <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
  <script>
    $(document).ready(function() {{
      $('#art-table').DataTable({{ pageLength: 5 }});
      $('#kw-table').DataTable({{ pageLength: 10 }});
    }});
  </script>
</body>
</html>"""

        # 5) Ausgabe schreiben
        with open(self.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[Dashboard] '{self.output}' erstellt.")

if __name__ == "__main__":
    DashboardGenerator().run()
