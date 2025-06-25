-- init.sql
DROP TABLE IF EXISTS realtime_anomalies;
CREATE TABLE realtime_anomalies (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    location VARCHAR(255),
    anomaly_reason VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_balance NUMERIC(18,2) NOT NULL
);

CREATE INDEX idx_anomaly_customer ON realtime_anomalies (customer_id);
CREATE INDEX idx_anomaly_time ON realtime_anomalies (detected_at);