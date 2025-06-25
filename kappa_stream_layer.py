import argparse
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pyflink.common import Types, Duration, Row
from pyflink.datastream import StreamExecutionEnvironment, RuntimeExecutionMode
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.datastream.connectors.kafka import KafkaSource,KafkaOffsetsInitializer
from pyflink.datastream.connectors.jdbc import JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.common.watermark_strategy import WatermarkStrategy, TimestampAssigner
from pyflink.datastream.functions import FlatMapFunction, RuntimeContext, FilterFunction, AggregateFunction
from pyflink.datastream.window import TumblingEventTimeWindows
from pyflink.common.time import Time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Utility Functions and Classes
# -----------------------------

def get_input_schema_from_kafka():
    return Types.ROW_NAMED(
        ["TransactionID", "CustomerID", "CustomerDOB", "CustGender", "CustLocation",
         "CustAccountBalance", "TransactionAmountINR", "EventTime"],
        [Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING(),
         Types.DOUBLE(), Types.DOUBLE(), Types.SQL_TIMESTAMP()]
    )
def log_and_filter(row, start, end):
    if row[7] is not None and  row[7] <= end:
        print(f"[Reprocess] Passing row: {row}")
        return True
    else:
        print(f"[Reprocess] Skipping row: {row}")
        return False
    
def is_anomalous(txn):
    transaction_amount = txn[6]
    cust_account_balance = txn[5]
    
    if transaction_amount is None or cust_account_balance is None:
        return []

    anomalies = []
    if transaction_amount > cust_account_balance * 0.5:
        anomalies.append("high_value_relative")
    if abs(transaction_amount) > 50000:
        anomalies.append("high_value_absolute")
    if (cust_account_balance - transaction_amount) < 0:
        anomalies.append("overdraft_attempt")
    
    return anomalies

class RecordTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, value, record_timestamp):
        return int(value[7].timestamp() * 1000)

class CustomerProfileAggregate(AggregateFunction):

    def create_accumulator(self):
        return {
            "customer_id":None,
            "total_amount": 0.0,
            "count": 0,
            "max_balance": 0.0,
            "location_freq": defaultdict(int)
        }

    def add(self, value, acc):
       
        transaction_amount = value[6]  # TransactionAmountINR
        account_balance = value[5]     # CustAccountBalance
        location = value[4]
        if acc["customer_id"] is None:            # CustLocation
            acc["customer_id"]=value[1]
        acc["total_amount"] += transaction_amount
        acc["count"] += 1
        acc["max_balance"] = max(acc["max_balance"], account_balance)
        acc["location_freq"][location] += 1
        return acc

    def get_result(self, acc):
        if acc["count"] == 0:
            return None

        top_location = max(acc["location_freq"].items(), key=lambda x: x[1])[0]
        avg_txn = acc["total_amount"] / acc["count"]

        # Dummy segment logic
        segment = "premium" if avg_txn > 15000 else "regular"

        return Row(
            acc["customer_id"],  # customer_id will be set after grouping
            round(avg_txn, 6),
            round(acc["max_balance"], 2),
            acc["count"],
            segment,
            datetime.utcnow(),
            top_location
        )

    def merge(self, acc1, acc2):
        acc1["total_amount"] += acc2["total_amount"]
        acc1["count"] += acc2["count"]
        acc1["max_balance"] = max(acc1["max_balance"], acc2["max_balance"])
        for loc, count in acc2["location_freq"].items():
            acc1["location_freq"][loc] += count
        return acc1

def attach_customer_id(cust_id, row):
    return Row(
        cust_id,
        row[1],  # avg_transaction
        row[2],  # max_balance
        row[3],  # transaction_count
        row[4],  # segment
        row[5],  # last_updated
        row[6]   # top_location
    )


def log_profile(row):
    print(f"[Profile] Aggregated profile: {row}")
    return row

class AnomalyDetection(FlatMapFunction):
    def open(self, runtime_context: RuntimeContext):
        logger.info("Initializing anomaly detector")

    def close(self):
        logger.info("Closing anomaly detector")

    def flat_map(self, transaction):
        try:
            transaction_id, customer_id, customer_dob, customer_gender, \
            cust_location, cust_account_balance, transaction_amount, event_time = transaction

            if None in (transaction_id, customer_id, cust_location):
                logger.warning("Incomplete transaction record %s", transaction)

            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time)
            elif not isinstance(event_time, datetime):
                raise ValueError("Invalid event_time format")

            anomalies = is_anomalous(transaction)
            logger.info(f"Processed transaction {transaction_id}, anomalies: {anomalies}")

            for reason in anomalies:
                yield Row(customer_id, transaction_id, float(transaction_amount),
                          cust_location, reason, cust_account_balance)

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")


# -----------------------------
# Main Flink Job
# -----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reprocess", action="store_true", help="Enable reprocessing mode")
    args = parser.parse_args()

    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10000)
    env.set_parallelism(1)

    env.add_jars(
        'file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar',
        'file:///opt/flink/lib/flink-connector-kafka-3.0.1-1.18.jar',
        'file:///opt/flink/lib/postgresql-42.6.0.jar',
        'file:///opt/flink/lib/flink-json-1.18.1.jar'
    )

   
    input_type_info = get_input_schema_from_kafka()

    deserialization_schema = JsonRowDeserializationSchema.builder() \
        .type_info(input_type_info) \
        .build()

    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers("kafka-kappa:9095") \
        .set_group_id("kappa_transaction_processors") \
        .set_topics("kappa-transactions") \
        .set_value_only_deserializer(deserialization_schema) \
        .set_starting_offsets(KafkaOffsetsInitializer.earliest() if args.reprocess else KafkaOffsetsInitializer.latest()) \
        .build()

    data_stream = env.from_source(
        source=kafka_source,
        watermark_strategy=WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_minutes(2))
            .with_timestamp_assigner(RecordTimestampAssigner()),
        source_name="KafkaSource"
    )

    if args.reprocess:
        logger.info("Running in batch reprocessing mode")

        now = datetime.now()
        ten_minutes_ago= now - timedelta(minutes=10)
        logger.info("Filtering records between %s and %s", ten_minutes_ago, now)


        filtered_stream = data_stream.filter(
        lambda row: log_and_filter(row, ten_minutes_ago, now)
        )

        customer_profile_type = Types.ROW_NAMED(
            ["customer_id", "avg_transaction", "max_balance", "transaction_count",
              "segment", "last_updated", "top_location"],
            [Types.STRING(), Types.BIG_DEC(), Types.BIG_DEC(), Types.LONG(), 
             Types.STRING(), Types.SQL_TIMESTAMP(), Types.STRING()]
        )
        reprocessed_profiles = filtered_stream \
        .key_by(lambda row: row[1], key_type=Types.STRING()) \
        .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
        .aggregate(CustomerProfileAggregate(), output_type=customer_profile_type)

        final_profiles= reprocessed_profiles.map(
            lambda row: log_profile(row),
            output_type=customer_profile_type
        )

        sink_sql_profiles = """
    INSERT INTO kappa_customer_profiles
    (customer_id, avg_transaction, max_balance, transaction_count, segment, last_updated, top_location)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (customer_id)
    DO UPDATE SET
        avg_transaction = EXCLUDED.avg_transaction,
        max_balance = EXCLUDED.max_balance,
        transaction_count = EXCLUDED.transaction_count,
        segment = EXCLUDED.segment,
        last_updated = EXCLUDED.last_updated,
        top_location = EXCLUDED.top_location
"""

        final_profiles.add_sink(
            JdbcSink.sink(
                sql=sink_sql_profiles,
                type_info=customer_profile_type,
                jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                    .with_url("jdbc:postgresql://postgres:5432/thesisdb")
                    .with_driver_name("org.postgresql.Driver")
                    .with_user_name("postgres")
                    .with_password("mysecretpassword")
                    .build(),
                jdbc_execution_options=JdbcExecutionOptions.builder()
                    .with_batch_size(1000)
                    .with_batch_interval_ms(100)
                    .build()
            )
        ).uid("profile_sink")

    else:
        logger.info("Running in real-time detection mode")

        anomaly_output_type = Types.ROW_NAMED(
            ['customer_id', 'transaction_id', 'amount', 'location', 'anomaly_reason', 'current_balance'],
            [Types.STRING(), Types.STRING(), Types.DOUBLE(), Types.STRING(), Types.STRING(), Types.DOUBLE()]
        )

        anomaly_stream = data_stream.flat_map(
            AnomalyDetection(), output_type=anomaly_output_type
        )

        anomaly_stream.map(lambda x: f"[Anomaly] {x}", output_type=Types.STRING()).print()

        sink_sql = """
            INSERT INTO kappa_realtime_anomalies
            (customer_id, transaction_id, amount, location, anomaly_reason, current_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        anomaly_stream.add_sink(
            JdbcSink.sink(
                sql=sink_sql,
                type_info=anomaly_output_type,
                jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                    .with_url("jdbc:postgresql://postgres:5432/thesisdb")
                    .with_driver_name("org.postgresql.Driver")
                    .with_user_name("postgres")
                    .with_password("mysecretpassword")
                    .build(),
                jdbc_execution_options=JdbcExecutionOptions.builder()
                    .with_batch_size(1000)
                    .with_batch_interval_ms(100)
                    .build()
            )
        ).uid("anomaly_sink")





    env.execute("Kappa Stream Layer Job")

if __name__ == "__main__":
    main()
