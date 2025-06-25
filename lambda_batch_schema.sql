CREATE TABLE customer_profiles (
    customer_id VARCHAR(255) PRIMARY KEY,
    segment VARCHAR(20) NOT NULL,  -- 'premium', 'standard', 'risky'
    avg_transaction DECIMAL(18,2),
    max_balance DECIMAL(18,2),
    top_location VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customer_segment ON customer_profiles (segment);