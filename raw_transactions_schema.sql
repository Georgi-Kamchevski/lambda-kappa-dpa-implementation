CREATE TABLE raw_transactions (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    customer_dob TEXT,
    customer_gender CHAR(1) CHECK (customer_gender IN ('M', 'F','X','T')),
    customer_location TEXT,
    customer_account_balance NUMERIC(12, 2),
    transaction_amount_inr NUMERIC(12, 2) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL
);
