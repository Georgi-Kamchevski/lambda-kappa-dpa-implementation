from confluent_kafka import Producer

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result """
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

# Producer configuration
conf = {
    'bootstrap.servers': 'localhost:9093',
    'client.id': 'my-producer'
}

# Create Producer instance
producer = Producer(conf)

# Produce messages
try:
    for i in range(10):
        producer.produce(
            'test-topic',  
            key=str(i+2),
            value=f'message {i+2}',
            callback=delivery_report
        )
       
        producer.poll(0)
    
    producer.flush()

except Exception as e:
    print(f'Exception occurred: {str(e)}')