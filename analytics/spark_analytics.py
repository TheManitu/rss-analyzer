# File: analytics/spark_analytics.py

import os
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, to_timestamp, explode,
    avg, expr, lit
)
from pyspark.sql.types import (
    StructType, StringType, IntegerType,
    ArrayType
)
import duckdb
from config import DB_PATH

# Pfade
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "storage" / "metrics_schema.sql"

# 1) Metrik-Tabellen sicherstellen
schema_sql = SCHEMA_FILE.read_text()
duckdb.connect(DB_PATH).execute(schema_sql).close()

# 2) Spark initialisieren
spark = SparkSession.builder.appName("RSS_QA_Analytics").getOrCreate()

# 3) JSON-Schemas
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
    .add("topic", StringType()) \
    .add("timestamp", StringType())

# 4) Kafka-Streams
kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
questions_raw = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap) \
    .option("subscribe", "UserQuestions") \
    .option("startingOffsets", "earliest").load()

views_raw = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap) \
    .option("subscribe", "ArticleViews") \
    .option("startingOffsets", "earliest").load()

# 5) JSON-Parsing
questions_df = questions_raw.select(from_json(col("value").cast("string"), question_schema).alias("q")) \
    .select("q.*").withColumn("ts", to_timestamp("timestamp"))

views_df = views_raw.select(from_json(col("value").cast("string"), view_schema).alias("v")) \
    .select("v.*").withColumn("ts", to_timestamp("timestamp"))

# 6) Aggregationen
topic_questions = questions_df.groupBy("topic").count() \
    .select(col("topic"), col("count").alias("question_count"))

candidate_stats = questions_df.agg(
    expr("count(*)").alias("total_questions"),
    avg("n_candidates").alias("avg_candidates"),
    expr("percentile_approx(n_candidates, 0.5)").alias("median_candidates"),
    expr("sum(case when n_candidates = 0 then 1 else 0 end)").alias("zero_candidate_count")
)

article_views = views_df.groupBy("article_id").count() \
    .select(col("article_id"), col("count").alias("view_count"))

article_refs = questions_df.select(explode("used_article_ids").alias("article_id")) \
    .groupBy("article_id").count() \
    .select(col("article_id"), col("count").alias("ref_count"))

article_metrics = article_views.join(article_refs, "article_id", "fullouter").na.fill(0)

# 7) Zeitreihenhistorie
def write_topic_questions_history(batch_df, batch_id):
    if not batch_df.rdd.isEmpty():
        with duckdb.connect(DB_PATH) as conn:
            for row in batch_df.collect():
                conn.execute("""
                    INSERT INTO topic_questions_history(timestamp, topic, question_count)
                    VALUES (CURRENT_TIMESTAMP, ?, ?)
                """, (row["topic"], row["question_count"]))

def write_candidate_stats_history(batch_df, batch_id):
    if not batch_df.rdd.isEmpty():
        stats = batch_df.collect()[0]
        with duckdb.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO question_stats_history(timestamp, total_questions, avg_candidates, median_candidates, zero_candidate_count)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
            """, (
                stats["total_questions"],
                stats["avg_candidates"],
                stats["median_candidates"],
                stats["zero_candidate_count"]
            ))

# 8) Artikel-Metriken + Rating
W_VIEW = 1.0
W_REF = 2.0

article_with_rating = article_metrics.withColumn(
    "rating_score",
    col("view_count") * lit(W_VIEW) + col("ref_count") * lit(W_REF)
)

def write_article_metrics(batch_df, batch_id):
    if not batch_df.rdd.isEmpty():
        with duckdb.connect(DB_PATH) as conn:
            for row in batch_df.collect():
                conn.execute("""
                    INSERT INTO article_metrics(article_id, view_count, ref_count, rating_score, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(article_id) DO UPDATE
                      SET view_count = excluded.view_count,
                          ref_count = excluded.ref_count,
                          rating_score = excluded.rating_score,
                          last_updated = CURRENT_TIMESTAMP
                """, (
                    row["article_id"],
                    row["view_count"],
                    row["ref_count"],
                    row["rating_score"]
                ))

# 9) Streams starten
topic_questions.writeStream.outputMode("update") \
    .foreachBatch(write_topic_questions_history).start()

candidate_stats.writeStream.outputMode("complete") \
    .foreachBatch(write_candidate_stats_history).start()

article_with_rating.writeStream.outputMode("update") \
    .foreachBatch(write_article_metrics).start()

# 10) Warten
spark.streams.awaitAnyTermination()
