import json
import time
import random
from faker import Faker
from confluent_kafka import Producer
from datetime import datetime, timedelta,timezone
import uuid

# Initialize Faker with Indian locale
fake = Faker('en_IN')

# Kafka Producer Configuration
conf = {
    'bootstrap.servers': 'localhost:29092', #localhost:29092 for Lambda mode, :29095 for Kappa mode
    'client.id': 'transaction-simulator',
    'queue.buffering.max.messages': 10,
    'queue.buffering.max.ms': 100,
    'batch.num.messages': 5,
    'linger.ms': 100,
    'message.timeout.ms': 5000
}

producer = Producer(conf)

TOPIC_NAME = 'transactions'

INDIAN_CITIES = [
    'MUMBAI', 'JAMSHEDPUR', 'JHAJJAR', 'NAVI MUMBAI', 'ITANAGAR',
    'GURGAON', 'MOHALI', 'GUNTUR', 'DELHI', 'BANGALORE',
    'HYDERABAD', 'CHENNAI', 'KOLKATA', 'PUNE', 'AHMEDABAD'
]

class TransactionTimeGenerator:
    def __init__(self):
        # Start simulation from 2017-01-01 00:00:00
        self.current_sim_time = datetime(2025, 1, 1)
        self.last_produce_time = time.time()
        self.transaction_counter = 0
        self.customer_ids = set()
        self.active_customers = []  # For repeat customers
    
    def generate_customer_id(self):
        """Generate customer ID with 30% chance of being returning customer"""
        if self.active_customers and random.random() < 0.3:
            return random.choice(self.active_customers)
        
        while True:
            cust_id = f"C{random.randint(1, 5)}"
            if cust_id not in self.customer_ids:
                self.customer_ids.add(cust_id)
                self.active_customers.append(cust_id)
            return cust_id
    

    def generate_transaction_id(self):
        uid = uuid.uuid4()
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
        return f"{timestamp}-{uid}"

        
    def get_next_time(self):
        """Get next timestamp with proper pacing"""
        now = time.time()
        elapsed = now - self.last_produce_time
        wait_time = random.uniform(1,2)
        
        if elapsed < wait_time:
            time.sleep(wait_time - elapsed)
        
        # Advance simulation time (faster than real-time for historical data)
        time_advance = timedelta(seconds=wait_time * 10)  # 10x speed for past data
        self.current_sim_time += time_advance
        
        # If we've caught up to present, switch to real-time
        if self.current_sim_time > datetime.now():
            self.current_sim_time = datetime.now()
        
        self.last_produce_time = time.time()
        
        return {
            'date': self.current_sim_time.strftime('%d/%m/%y'),
            'time': self.current_sim_time.strftime('%H%M%S'),
            'datetime': self.current_sim_time.strftime('%Y-%m-%dT%H:%M:%S')
        }
def generate_event_time():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def generate_customer_dob():
    """Generate DOB between 1950-2000"""
    start_date = datetime(1950, 1, 1)
    end_date = datetime(2000, 12, 31)
    dob_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return dob_date.strftime('%d/%m/%y')

def delivery_report(err, msg):
    """Callback for message delivery status"""
    if err is not None:
        print(f'Delivery failed: {err}')
    else:
        print(f'Delivered to {msg.topic()}[{msg.partition()}] @ offset {msg.offset()}')

def produce_with_pacing():
    time_gen = TransactionTimeGenerator()
    message_count = 0
    
    try:
        while True:
            # Generate record with proper IDs and timing
            time_data = time_gen.get_next_time()
            
            # 30% chance of negative transaction (withdrawal)
            amount = round(random.uniform(100, 60000), 2)
            if random.random() < 0.3:
                amount = round(random.uniform(-60000, -100), 2)
            
            record = {
                'TransactionID': time_gen.generate_transaction_id(),
                'CustomerID': time_gen.generate_customer_id(),
                'CustomerDOB': generate_customer_dob(),
                'CustGender': random.choice(['M', 'F']),
                'CustLocation': random.choice(INDIAN_CITIES),
                'CustAccountBalance': round(random.uniform(0, 1000000), 2),
                'TransactionAmountINR': amount,
                'EventTime': generate_event_time()
            }
            
            # Produce message
            producer.produce(
                TOPIC_NAME,
                json.dumps(record).encode('utf-8'),
                callback=delivery_report
            )
            
            message_count += 1
            print(f"Sent T{time_gen.transaction_counter} {record["CustomerID"]} ({time_data['datetime']}): {amount} INR")
            
            # Regular polling and pacing
            producer.poll(0.1)
            
            # If simulating historical data, go faster
            if time_gen.current_sim_time < datetime.now() - timedelta(days=30):
                time.sleep(0.1)  # Fast playback for old data
            else:
                time.sleep(max(1, random.uniform(2, 5)))
                
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        print(f"Flushing remaining messages...")
        producer.flush()
        print(f"Total produced: {message_count}")
        print(f"Last Transaction ID: T{time_gen.transaction_counter}")

if __name__ == '__main__':
    print("Starting transaction simulator (2025-present)")
    
    produce_with_pacing()