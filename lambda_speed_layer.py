from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream.connectors.jdbc import JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.datastream.functions import ProcessFunction, RuntimeContext
from pyflink.common import Row
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_input_schema():
    return Types.ROW_NAMED(
        ["TransactionID", "CustomerID","CustomerDOB" ,"CustGender","CustLocation", 
         "CustAccountBalance", "TransactionAmountINR", "EventTime"],
        [Types.STRING(), Types.STRING(),Types.STRING(),Types.STRING(),Types.STRING(),
         Types.DOUBLE(), Types.DOUBLE(), Types.SQL_TIMESTAMP()]
    )

class AnomalyDetector(ProcessFunction):
    def open(self, runtime_context: RuntimeContext):
        logger.info("Initializing anomaly detector")

    def close(self):
        logger.info("Closing anomaly detector")

    def process_element(self, input_transaction, ctx):
        try:
            (transaction_id,
            customer_id,
            customer_dob,
            cust_gender,
            cust_location,
            cust_account_balance,
            transaction_amount,
            event_time) = input_transaction

            if None in (transaction_id, customer_id, cust_location):
                logger.warning("Incomplete transaction record: %s", input_transaction)
                return

            # Convert timestamp if needed
            if isinstance(event_time, str):
                transaction_time = datetime.fromisoformat(event_time)
            else:
                transaction_time = event_time 

            anomalies = []
            if transaction_amount > cust_account_balance * 0.5:
                anomalies.append("high_value_relative")
            if abs(transaction_amount) > 50000:
                anomalies.append("high_value_absolute")
            if (cust_account_balance - transaction_amount) < 0:
                anomalies.append("overdraft_attempt")

            logger.info(f"Processed transaction {transaction_id}, balance: {cust_account_balance}, anomalies: {anomalies}")

            for reason in anomalies:
                yield Row(
                    customer_id,
                    transaction_id,
                    float(transaction_amount),
                    cust_location,
                    reason,
                    cust_account_balance
                )

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10000)  # 10 second checkpoints
    env.set_parallelism(1)

    # Add required connectors
    env.add_jars(
        'file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar',
        'file:///opt/flink/lib/flink-connector-kafka-3.0.1-1.18.jar',
        'file:///opt/flink/lib/postgresql-42.6.0.jar',
        'file:///opt/flink/lib/flink-json-1.18.1.jar'
    )
    print("Schema being passed to type_info:", get_input_schema())

    # Kafka source with watermark strategy
    kafka_consumer = FlinkKafkaConsumer(
        topics="transactions",
        deserialization_schema=JsonRowDeserializationSchema.builder()
            .type_info(get_input_schema()).build(),
        properties={
            'bootstrap.servers': 'kafka:9092',
            'group.id': 'flink-anomaly-detection',
            'auto.offset.reset': 'earliest',
            'key.deserializer': 'org.apache.kafka.common.serialization.ByteArrayDeserializer',
            'value.deserializer': 'org.apache.kafka.common.serialization.ByteArrayDeserializer'
        }
    )
    kafka_consumer.set_start_from_earliest()

    # Output type matching PostgreSQL schema
    output_type = Types.ROW_NAMED(
    ['customer_id', 'transaction_id', 'amount', 'location', 
     'anomaly_reason', 'current_balance'],  # Removed detected_at
    [Types.STRING(), Types.STRING(), Types.DOUBLE(), Types.STRING(),
     Types.STRING(), Types.DOUBLE()]
)
    # Pipeline construction
    source_stream = env.add_source(kafka_consumer)

    raw_stream = source_stream
    anomalies_stream = source_stream.process(AnomalyDetector(), output_type=output_type)

    anomalies_stream.print()

    # JDBC sink configuration
    anomalies_stream.add_sink(
        JdbcSink.sink(
            """INSERT INTO realtime_anomalies 
                (customer_id, transaction_id, amount, location, 
                anomaly_reason, current_balance) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,  # 6 params now
            type_info=output_type,
            jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .with_url("jdbc:postgresql://postgres:5432/thesisdb")
                .with_driver_name("org.postgresql.Driver")
                .with_user_name("postgres")
                .with_password("mysecretpassword")
                .build(),
            jdbc_execution_options=JdbcExecutionOptions.builder()
                .with_batch_interval_ms(1000)
                .with_batch_size(100)
                .build()
        )
    )

    raw_output_type = Types.ROW_NAMED(
    [ 'transaction_id','customer_id','customer_dob','customer_gender',  'customer_location',
     'customer_account_balance','transaction_amount_inr','event_time'],  # Removed detected_at
    [Types.STRING(), Types.STRING(),Types.STRING(),Types.STRING(),Types.STRING(), Types.DOUBLE(), 
     Types.DOUBLE(), Types.SQL_TIMESTAMP()]
    )

    raw_stream.add_sink(
        JdbcSink.sink("""
        INSERT INTO raw_transactions 
       (transaction_id, customer_id, customer_dob, customer_gender, customer_location, 
        customer_account_balance, transaction_amount_inr, event_time) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (transaction_id) DO NOTHING

        """,   
     type_info=raw_output_type,
            jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .with_url("jdbc:postgresql://postgres:5432/thesisdb")
                .with_driver_name("org.postgresql.Driver")
                .with_user_name("postgres")
                .with_password("mysecretpassword")
                .build(),
            jdbc_execution_options=JdbcExecutionOptions.builder()
                .with_batch_interval_ms(1000)
                .with_batch_size(100)
                .build()
        )
        )

    env.execute("AnomalyDetection")

if __name__ == "__main__":
    main()