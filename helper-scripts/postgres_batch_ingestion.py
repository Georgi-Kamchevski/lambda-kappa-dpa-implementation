from pyspark.sql import SparkSession
import pyspark.sql.functions  as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
from py4j.java_gateway import java_import # Define schema matching your Kafka JSON

transaction_schema = StructType([
    StructField("TransactionID",StringType()),
    StructField("CustomerID", StringType()),
    StructField("CustomerDOB", StringType()),
    StructField("CustGender", StringType()),
    StructField("CustLocation", StringType()),
    StructField("CustAccountBalance", DoubleType()),
    StructField("TransactionAmountINR", DoubleType()),
    StructField("EventTime",TimestampType())
])



# Initialize Spark with explicit driver config
spark = SparkSession.builder \
    .appName("DailyTransactionReports") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0") \
    .config("spark.driver.extraClassPath", "/opt/bitnami/spark/.ivy2/jars/org.postgresql_postgresql-42.6.0.jar") \
    .config("spark.executor.extraClassPath", "/opt/bitnami/spark/.ivy2/jars/org.postgresql_postgresql-42.6.0.jar") \
    .config("spark.sql.verbose", "true") \
    .config("spark.driver.extraJavaOptions", "-Dlog4j.configuration=file:/path/to/log4j-debug.properties") \
    .getOrCreate()

# MANUALLY REGISTER DRIVER (Critical for JDBC)
try:
    java_import(spark._jvm, "org.postgresql.Driver")
    print("✅ PostgreSQL driver registered successfully")
except Exception as e:
    print(f"❌ Driver registration failed: {str(e)}")
    raise

# Read from Kafka
kafka_df = spark.read.format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "earliest") \
    .load()

kafka_df_count=kafka_df.count()



df=kafka_df.select(
    F.from_json(F.col("value").cast("string"),transaction_schema).alias("data")
).select("data.*")

df.select("TransactionAmountINR").summary().show()





processed_count=df.count()
df.show(200,truncate=False)
print("\n\n"+"Records ingested:"+str(kafka_df_count)+" Records processed:"+str(processed_count)+"\n\n")
# Write to PostgreSQL

df = df \
    .withColumnRenamed("TransactionID", "transaction_id") \
    .withColumnRenamed("CustomerID", "customer_id") \
    .withColumnRenamed("CustLocation", "customer_location") \
    .withColumnRenamed("CustomerDOB", "customer_dob") \
    .withColumnRenamed("CustGender", "customer_gender") \
    .withColumnRenamed("CustAccountBalance", "customer_account_balance") \
    .withColumnRenamed("TransactionAmountINR", "transaction_amount_inr")\
    .withColumnRenamed("EventTime", "event_time")


df.write \
    .format("jdbc")\
        .option("url", "jdbc:postgresql://postgres:5432/thesisdb?loggerLevel=DEBUG")\
        .option("driver", "org.postgresql.Driver")\
            .option("dbtable", "raw_transactions")\
                .option("user", "postgres")\
                    .option("password", "mysecretpassword")\
                    .option("batchsize", "10000")\
                    .mode("append").save()



spark.stop()