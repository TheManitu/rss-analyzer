from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp
from pyspark.sql.types import StructType, StringType, TimestampType

def main():
    # 1) Spark‑Session initialisieren
    spark = (SparkSession.builder
             .appName("AnalyticsStream")
             .getOrCreate())

    # 2) Schema für UserQuestion‑Events definieren
    question_schema = (StructType()
        .add("type", StringType())
        .add("question", StringType())
        .add("topic", StringType())
        .add("timestamp", StringType())
    )

    # 3) Stream von Kafka‑Topic UserQuestions lesen
    raw_q = (spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "UserQuestions")
        .option("startingOffsets", "earliest")
        .load()
    )

    # 4) JSON parsen und Timestamp umwandeln
    parsed_q = (raw_q.select(from_json(col("value").cast("string"), question_schema).alias("j"))
        .select("j.*")
        .withColumn("ts", to_timestamp("timestamp"))
    )

    # 5) Top 10 gestellte Fragen (kompletter Modus)
    top_q = (parsed_q
        .groupBy("question")
        .count()
        .orderBy(col("count").desc())
        .limit(10)
    )

    # 6) Ausgabe in Konsole
    q_query = (top_q.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .start()
    )

    # 7) Schema für ArticleViewed‑Events definieren
    view_schema = (StructType()
        .add("type", StringType())
        .add("article_id", StringType())
        .add("user_id", StringType())
        .add("timestamp", StringType())
    )

    # 8) Stream von Kafka‑Topic ArticleViews lesen
    raw_v = (spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "ArticleViews")
        .option("startingOffsets", "earliest")
        .load()
    )

    # 9) JSON parsen
    parsed_v = (raw_v.select(from_json(col("value").cast("string"), view_schema).alias("j"))
        .select("j.*")
        .withColumn("ts", to_timestamp("timestamp"))
    )

    # 10) Top 10 meistgelesene Artikel
    top_v = (parsed_v
        .groupBy("article_id")
        .count()
        .orderBy(col("count").desc())
        .limit(10)
    )

    # 11) Ausgabe in Konsole
    v_query = (top_v.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .start()
    )

    # 12) Auf Streams warten
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
