from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, desc
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

def main():
    spark = SparkSession.builder \
        .appName("KafkaUserQuestionsAnalysis") \
        .getOrCreate()

    # Schema für die eingehenden Kafka-Nachrichten definieren
    schema = StructType([
        StructField("question", StringType(), True),
        StructField("topic", StringType(), True)
    ])

    # Lese von Kafka (ersetze bootstrap-servers durch Deinen Kafka-Cluster)
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "rss-kafka-ingest:9092") \
        .option("subscribe", "UserQuestions") \
        .option("startingOffsets", "earliest") \
        .load()

    # Konvertiere den Wert von Kafka (Binärdaten) in einen String und parse JSON
    questions_df = df.selectExpr("CAST(value AS STRING) as json_str", "timestamp") \
        .select(from_json(col("json_str"), schema).alias("data"), "timestamp") \
        .select("data.*", "timestamp")

    # Aggregiere die am häufigsten gestellten Fragen in einem 1-Minuten-Fenster
    agg_df = questions_df.groupBy(
        window(col("timestamp"), "1 minute"),
        col("question")
    ).agg(count("*").alias("count")).orderBy(desc("count"))

    query = agg_df.writeStream \
        .outputMode("complete") \
        .format("console") \
        .option("truncate", "false") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
