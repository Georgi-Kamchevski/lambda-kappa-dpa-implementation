import pandas as pd
import random
import argparse

def sign_transactions(input_file, output_file, withdrawal_prob=0.6):
    """Adds random signs to transactions without any grouping."""
    df = pd.read_csv(input_file)
    
    # Validate and convert
    if 'TransactionAmount (INR)' not in df.columns:
        raise ValueError("Missing 'TransactionAmount (INR)' column")
    
    df['TransactionAmount (INR)'] = pd.to_numeric(
        df['TransactionAmount (INR)'], 
        errors='coerce'
    )
    
    # Add signs directly (no grouping needed)
    df['TransactionAmount (INR)'] = df['TransactionAmount (INR)'].apply(
        lambda x: -abs(x) if random.random() < withdrawal_prob else abs(x)
    )
    
    # Save
    df.to_csv(output_file, index=False)
    print(f"Added signs to {len(df)} transactions. Sample:")
    print(df[['CustomerID', 'TransactionAmount (INR)']].head(3))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input CSV path")
    parser.add_argument("output", help="Output CSV path")
    parser.add_argument("--withdrawal_prob", type=float, default=0.6,
                       help="Probability of withdrawal (0-1)")
    args = parser.parse_args()
    
    sign_transactions(args.input, args.output, args.withdrawal_prob)