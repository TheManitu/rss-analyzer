# analytics/spark_quality_checks.py

import os
import duckdb
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode
from pyspark.sql.types import (
    StructType, StringType, DoubleType, BooleanType, ArrayType
)

def main():
    # 1) SparkSession initialisieren
    spark = SparkSession.builder \
        .appName("AnswerQualityStream") \
        .getOrCreate()

    # 2) Schema für AnswerQuality-Events
    quality_schema = StructType() \
        .add("type", StringType()) \
        .add("used_article_ids", ArrayType(StringType())) \
        .add("quality_score", DoubleType()) \
        .add("flag", BooleanType()) \
        .add("user_id", StringType()) \
        .add("session_id", StringType()) \
        .add("timestamp", StringType())

    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
    topic_quality  = os.getenv("TOPIC_ANSWER_QUALITY", "AnswerQuality")
    db_path        = os.getenv("DB_PATH", "/app/data/rssfeed.duckdb")

    # 3) Kafka-Stream lesen
    raw_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap) \
        .option("subscribe", topic_quality) \
        .option("startingOffsets", "earliest") \
        .load()

    # 4) JSON parsen
    parsed_df = raw_df.select(
        from_json(col("value").cast("string"), quality_schema).alias("q")
    ).select(
        col("q.timestamp").alias("timestamp"),
        col("q.used_article_ids").alias("used_article_ids"),
        col("q.quality_score").alias("quality_score"),
        col("q.flag").alias("flag"),
        col("q.user_id").alias("user_id"),
        col("q.session_id").alias("session_id")
    )

    # 5) Explodiere die Liste der genutzten Artikel
    exploded_df = parsed_df.select(
        col("timestamp"),
        explode(col("used_article_ids")).alias("link"),
        col("quality_score"),
        col("flag"),
        col("user_id"),
        col("session_id")
    )

    # 6) Schreibe in DuckDB via foreachBatch
    def write_batch(batch_df, batch_id):
        conn = duckdb.connect(db_path)
        # Tabelle anlegen, falls nicht vorhanden
        conn.execute("""
            CREATE TABLE IF NOT EXISTS answer_quality_events (
                timestamp     TIMESTAMP,
                link          TEXT,
                quality_score DOUBLE,
                flag          BOOLEAN,
                user_id       TEXT,
                session_id    TEXT
            );
        """)
        rows = batch_df.collect()
        for r in rows:
            conn.execute(
                "INSERT INTO answer_quality_events VALUES (?, ?, ?, ?, ?, ?)",
                (r["timestamp"], r["link"], r["quality_score"],
                 r["flag"], r["user_id"], r["session_id"])
            )
        conn.close()

    exploded_df.writeStream \
        .outputMode("append") \
        .foreachBatch(write_batch) \
        .start()

    # 7) Job laufen lassen
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()
