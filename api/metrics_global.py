# api/metrics_global.py

from prometheus_client import Counter, Gauge, Histogram

# Einmalige Definition der Metriken – keine Duplikate!
Q_COUNT    = Counter(
    "rss_questions_total",
    "Total number of questions processed"
)
ZERO_CAND  = Gauge(
    "rss_zero_candidate_ratio",
    "Ratio of questions with zero candidates"
)
DB_LATENCY = Histogram(
    "duckdb_query_seconds",
    "DuckDB query latency in seconds"
)
