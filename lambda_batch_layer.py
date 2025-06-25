from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from py4j.java_gateway import java_import

# Initialize Spark session
spark = SparkSession.builder \
    .appName("LambdaBatchCustomerProfiles") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0") \
    .config("spark.driver.extraClassPath", "/opt/bitnami/spark/.ivy2/jars/org.postgresql_postgresql-42.6.0.jar") \
    .config("spark.executor.extraClassPath", "/opt/bitnami/spark/.ivy2/jars/org.postgresql_postgresql-42.6.0.jar") \
    .getOrCreate()

# Register JDBC driver
try:
    java_import(spark._jvm, "org.postgresql.Driver")
    print("PostgreSQL driver registered successfully")
except Exception as e:
    print(f"Driver registration failed: {str(e)}")
    raise

#  Read raw transactions from PostgreSQL
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres:5432/thesisdb") \
    .option("dbtable", "raw_transactions") \
    .option("user", "postgres") \
    .option("password", "mysecretpassword") \
    .option("driver", "org.postgresql.Driver") \
    .load()

df.printSchema()

# Compute top locations per customer
top_locations = (
    df.groupBy("customer_id", "customer_location")
      .agg(F.count("*").alias("cnt"))
      .groupBy("customer_id")
      .agg(F.max(F.struct("cnt", "customer_location")).alias("max_loc"))
      .select("customer_id", F.col("max_loc.customer_location").alias("top_location"))
)

#  Compute customer segments
customer_segments = (
    df.groupBy("customer_id")
      .agg(
          F.avg("transaction_amount_inr").alias("avg_transaction"),
          F.max("customer_account_balance").alias("max_balance"),
          F.count("*").alias("transaction_count")
      )
      .withColumn(
          "segment",
          F.when(F.col("avg_transaction") > 50000, "premium")
           .when(F.col("transaction_count") > 10, "frequent")
           .otherwise("standard")
      )
      .withColumn("last_updated", F.current_timestamp())
)

#  Join segments and top locations
final_result = customer_segments.join(top_locations, on="customer_id", how="left")

final_result.show(200, truncate=False)

# Write to PostgreSQL (overwrite for now — can switch to merge later)
final_result.write \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres:5432/thesisdb") \
    .option("dbtable", "customer_profiles") \
    .option("user", "postgres") \
    .option("password", "mysecretpassword") \
    .option("driver", "org.postgresql.Driver") \
    .mode("overwrite") \
    .save()

spark.stop()
