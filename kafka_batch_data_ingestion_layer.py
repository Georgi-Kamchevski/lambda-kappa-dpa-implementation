from confluent_kafka import Producer
import pandas as pd
import json
import time
import uuid
from datetime import datetime, timezone

# configuring Kafka
conf = {
        'bootstrap.servers':'localhost:29092',
        'error_cb': lambda err: print(f"Kafka error: {err}"),
        'batch.num.messages': 100000,  # Default is 10000 (reduce if needed)
        'queue.buffering.max.ms': 100,
        'debug': 'broker,protocol'  # Enable debug logs
    }
producer = Producer(conf)

chunk_size = 100000
total_records = 0

def generate_transaction_id():
    uid = uuid.uuid4()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f"{timestamp}-{uid}"

def generate_event_time():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

seen_ids = set()
duplicate_count = 0

for chunk in pd.read_csv('bank_transactions.csv', chunksize=chunk_size):
    for _, row in chunk.iterrows():
        transaction_id = generate_transaction_id()
        event_time=generate_event_time()
        kafka_value = {
            "TransactionID": transaction_id,
            "CustomerID": row["CustomerID"],
            "CustomerDOB": row["CustomerDOB"],
            "CustGender": row["CustGender"],
            "CustLocation": row['CustLocation'],
            "CustAccountBalance": row['CustAccountBalance'],
            "TransactionAmountINR": row['TransactionAmount (INR)'],
            "EventTime": event_time
        }

        if transaction_id in seen_ids:
            print(f"[WARNING] Duplicate TransactionID detected: {transaction_id}")
            duplicate_count += 1
        seen_ids.add(transaction_id)

        json_value = json.dumps(kafka_value)
        msg_size = len(json_value.encode('utf-8'))
        producer.produce(
            topic="transactions",
            value=json_value
        )

    producer.flush()
    total_records += len(chunk)

print(f"Successfully ingested {total_records} records into Kafka.")
