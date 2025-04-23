from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, DoubleType, BooleanType, TimestampType

def main():
    spark = (SparkSession.builder
             .appName("QualityChecks")
             .getOrCreate())

    # Schema für die Quality‑Events (muss von Deinem QualityEvaluator in Kafka kommen)
    quality_schema = (StructType()
        .add("type", StringType())
        .add("score", DoubleType())
        .add("flag", BooleanType())
        .add("timestamp", StringType())
    )

    # Lesen des Topics AnswerQuality
    raw_q = (spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "AnswerQuality")
        .option("startingOffsets", "earliest")
        .load()
    )

    parsed_q = (raw_q.select(from_json(col("value").cast("string"), quality_schema).alias("q"))
        .select("q.*")
    )

    # 1) Durchschnittliche Qualität pro Minute
    avg_score = (parsed_q
        .groupBy()
        .avg("score")
    )

    avg_query = (avg_score.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .start()
    )

    # 2) Flagged‑Events zählen
    flagged = (parsed_q.filter(col("flag") == True)
        .groupBy()
        .count().alias("flagged_count")
    )

    flag_query = (flagged.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .start()
    )

    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
