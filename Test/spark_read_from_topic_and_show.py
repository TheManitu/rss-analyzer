from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("KafkaSparkIntegration") \
    .getOrCreate()

df = spark \
    .read \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka2:9092") \
    .option("subscribe", "RSSTopic") \
    .option("kafka.partition.assignment.strategy", "org.apache.kafka.clients.consumer.RangeAssignor") \
    .load()

df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)") \
  .show(truncate=False)

spark.stop()
