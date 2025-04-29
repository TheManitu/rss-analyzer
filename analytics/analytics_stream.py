from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp, explode, avg, expr, when
from pyspark.sql.types import StructType, StringType, IntegerType, ArrayType, TimestampType

# 1. Spark-Session initialisieren
spark = SparkSession.builder.appName("RSS_QA_Analytics").getOrCreate()

# 2. Schemas definieren für JSON-Parsing
question_schema = StructType() \
    .add("type", StringType()) \
    .add("question", StringType()) \
    .add("topic", StringType()) \
    .add("n_candidates", IntegerType()) \
    .add("used_article_ids", ArrayType(IntegerType())) \
    .add("timestamp", StringType())

view_schema = StructType() \
    .add("type", StringType()) \
    .add("article_id", IntegerType()) \
    .add("user_id", StringType()) \
    .add("timestamp", StringType())

# 3. Kafka-Streams lesen (als Quelle dienen die Topics)
questions_raw_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "UserQuestions") \
    .option("startingOffsets", "earliest").load()

views_raw_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "ArticleViews") \
    .option("startingOffsets", "earliest").load()

# 4. JSON parsen und Datentypen konvertieren
questions_df = questions_raw_df.select(from_json(col("value").cast("string"), question_schema).alias("q")) \
    .select("q.*") \
    .withColumn("ts", to_timestamp("timestamp"))

views_df = views_raw_df.select(from_json(col("value").cast("string"), view_schema).alias("v")) \
    .select("v.*") \
    .withColumn("ts", to_timestamp("timestamp"))

# Optional: Artikel-Stammdaten als statische Tabelle laden, um Topic oder Titel hinzuzufügen
# (Hier beispielhaft via DuckDB-JDBC; alternativ via DuckDB-Python außerhalb von Spark)
# articles_static = spark.read.format("jdbc")... option("url", "jdbc:duckdb:/path/to/db") \
#    .option("dbtable", "articles").load()
# -> enthält Spalten: id, title, topic, etc.

# 5. Aggregation: Top-Themen nach Views
# Füge Topic zu View-Events hinzu (hier angenommen, es wurde im Event mitgeliefert oder via Join mit articles_static)
# Beispiel: wenn articles_static vorhanden:
# views_with_topic = views_df.join(articles_static.select("id","topic"), views_df.article_id == articles_static.id)
# else, falls topic im Event nicht vorhanden, muss über article_id gemappt werden, bspw. offline.
views_with_topic = views_df  # (angenommen articleViews enthält bereits Topic via Logging oder join wie oben)
top_topics_views = views_with_topic.groupBy("topic").count().alias("view_count")

# Aggregation: Top-Themen nach Fragen
top_topics_questions = questions_df.groupBy("topic").count().alias("question_count")

# Hinweis: Die beiden DataFrames `top_topics_views` und `top_topics_questions` enthalten je eine Spalte "topic" und eine Count-Spalte.
# Man könnte sie zusammenführen, z.B. per join on topic (stream-stream join mit watermark nötig) oder indem man beide nach DuckDB schreibt und dort joined.
# Für Einfachheit schreiben wir sie getrennt nach DuckDB und kombinieren dort.

# 6. Aggregation: Kandidaten-Statistiken aus Fragen
candidate_stats_df = questions_df.agg(
    expr("count(*)").alias("total_questions"),
    avg("n_candidates").alias("avg_candidates"),
    expr("percentile_approx(n_candidates, 0.5)").alias("median_candidates"),
    expr("sum(case when n_candidates = 0 then 1 else 0 end)").alias("zero_candidate_count")
)

# 7. Aggregation: Artikel-Referenzen aus Fragen 
# (jeder Artikel, der in used_article_ids vorkommt, wird als einzelnes Event gezählt)
article_refs_df = questions_df.select(explode("used_article_ids").alias("article_id")) \
    .groupBy("article_id").count().alias("ref_count")

# Aggregation: Artikel-Views
article_views_df = views_df.groupBy("article_id").count().alias("view_count")

# Für Artikel-Metriken beide zusammenführen:
# Hier stream-stream-join auf article_id; um Komplexität zu reduzieren, könnte man stattdessen in DuckDB mergen.
# Wir illustrieren einen möglichen join mit Wasserzeichen (sofern ts vorhanden):
article_views_df = article_views_df.withWatermark("article_id", "0 seconds")
article_refs_df = article_refs_df.withWatermark("article_id", "0 seconds")
article_metrics_df = article_views_df.join(article_refs_df, "article_id", "fullouter") \
    .na.fill(0)  # fehlende Werte durch 0 ersetzen
# article_metrics_df enthält nun pro article_id view_count und ref_count; Quality kommt später hinzu.

# 8. Ergebnisse in DuckDB schreiben mittels foreachBatch
# Hilfsfunktion zum Upsert in DuckDB
def write_article_metrics(batch_df, batch_id):
    import duckdb
    conn = duckdb.connect("/path/to/analytics.db")  # Pfad zur DuckDB-Datei
    # Upsert jede Zeile: falls article_id schon existiert, aktualisieren, sonst einfügen.
    for row in batch_df.collect():
        aid = row["article_id"]
        views = row.get("view_count", 0)
        refs = row.get("ref_count", 0)
        conn.execute("""
            INSERT INTO article_metrics(article_id, views, question_refs, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (article_id) DO UPDATE
            SET views=excluded.views + article_metrics.views, 
                question_refs=excluded.question_refs + article_metrics.question_refs,
                last_updated=CURRENT_TIMESTAMP;
            """, (aid, views, refs))
    conn.close()

# Start Streaming Query für article_metrics (Views/Refs Zähler)
article_query = article_metrics_df.writeStream.outputMode("update") \
    .foreachBatch(write_article_metrics).start()

# Ebenso: Top-Themen (Views und Questions) -> DuckDB (z.B. in getrennte Tabellen oder direkt kombinieren)
def write_topic_views(batch_df, batch_id):
    import duckdb
    conn = duckdb.connect("/path/to/analytics.db")
    for row in batch_df.collect():
        topic = row["topic"]
        count = row["count"]
        conn.execute("""
            INSERT INTO topic_metrics(topic, total_views, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(topic) DO UPDATE
            SET total_views = ?, last_updated = CURRENT_TIMESTAMP;
        """, (topic, count, count))
    conn.close()

topic_views_query = top_topics_views.writeStream.outputMode("complete") \
    .foreachBatch(write_topic_views).start()

def write_topic_questions(batch_df, batch_id):
    import duckdb; conn = duckdb.connect("/path/to/analytics.db")
    for row in batch_df.collect():
        topic = row["topic"]; qcount = row["count"]
        conn.execute("""
            INSERT INTO topic_metrics(topic, total_questions, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(topic) DO UPDATE
            SET total_questions = ?, last_updated = CURRENT_TIMESTAMP;
        """, (topic, qcount, qcount))
    conn.close()

topic_q_query = top_topics_questions.writeStream.outputMode("complete") \
    .foreachBatch(write_topic_questions).start()

# Kandidaten-Statistiken -> DuckDB (z.B. Tabelle question_stats mit Einzelzeile)
def write_question_stats(batch_df, batch_id):
    import duckdb; conn = duckdb.connect("/path/to/analytics.db")
    stats = batch_df.collect()[0]  # Batch hat genau eine Zeile
    conn.execute("DELETE FROM question_stats;")  # alte Stats löschen (halten nur aktuellen Stand)
    conn.execute("""
        INSERT INTO question_stats(total_questions, avg_candidates, median_candidates, zero_candidate_count, timestamp)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, (int(stats["total_questions"]), float(stats["avg_candidates"]), 
          float(stats["median_candidates"]), int(stats["zero_candidate_count"])))
    conn.close()

stats_query = candidate_stats_df.writeStream.outputMode("complete") \
    .foreachBatch(write_question_stats).start()

# 9. Abwarten bis Streams beendet (in realem Job meist infinite laufend)
spark.streams.awaitAnyTermination()
