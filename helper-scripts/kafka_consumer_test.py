from confluent_kafka import Consumer

# Consumer configuration
conf = {
    'bootstrap.servers': 'kafka:9093',
    'group.id': 'my-group',
    'auto.offset.reset': 'latest'
}

# Create Consumer instance
consumer = Consumer(conf)

# Subscribe to topic
consumer.subscribe(['transactions'])

try:
    while True:
        msg = consumer.poll(1.0)  # Timeout in seconds
        
        if msg is None:
            continue
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

        print(f"Received message: {msg.value().decode('utf-8')}")

except KeyboardInterrupt:
    pass
finally:
    # Close down consumer to commit final offsets
    consumer.close()