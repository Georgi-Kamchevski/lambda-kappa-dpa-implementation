# jdbc_test.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common import Row
from pyflink.common.typeinfo import Types
from pyflink.datastream.connectors.jdbc import JdbcSink, JdbcConnectionOptions
from pyflink.datastream.connectors.jdbc import JdbcExecutionOptions

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    # Single test row
    ds = env.from_collection(
        [Row("C_TEST", "T_TEST", 123.45, "LOC", "debug")],
        type_info=Types.ROW_NAMED(
            ["customer_id","transaction_id","amount","location","anomaly_reason"],
            [Types.STRING(), Types.STRING(), Types.DOUBLE(), Types.STRING(), Types.STRING()]
        )
    )
    ds.print()

    ds.add_sink(
        JdbcSink.sink(
            "INSERT INTO test_anomalies (customer_id,transaction_id,amount,location,anomaly_reason) VALUES(?,?,?,?,?)",
            type_info=Types.ROW([
                Types.STRING(), Types.STRING(), Types.DOUBLE(),
                Types.STRING(), Types.STRING()
            ]),
            jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .with_url("jdbc:postgresql://postgres:5432/thesisdb")
                .with_driver_name("org.postgresql.Driver")
                .with_user_name("postgres")
                .with_password("mysecretpassword")
                .build(),
            jdbc_execution_options=JdbcExecutionOptions.builder()
                .with_batch_size(1)
                .with_batch_interval_ms(1000)
                .build()
        )
    )

    env.execute("JDBC_Test")

if __name__ == "__main__":
    main()
