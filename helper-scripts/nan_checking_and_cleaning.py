import pandas as pd
import argparse
from pathlib import Path

def load_and_clean_data(input_path, nan_strategy='report', custom_fills=None):
    """
    Load CSV with comprehensive NaN handling.
    
    Args:
        input_path: Path to CSV file
        nan_strategy: 'report', 'drop', 'fill_mean', 'fill_median', 'fill_mode', 'custom'
        custom_fills: Dictionary of {column: fill_value} pairs
    Returns:
        Cleaned DataFrame
    """
    # Load data with type inference
    df = pd.read_csv(input_path, infer_datetime_format=True, parse_dates=True)
    
    # NaN Analysis
    nan_report = df.isna().sum()
    print("\nNaN Values Before Handling:")
    print(nan_report[nan_report > 0].to_string())
    
    # Handle NaNs based on strategy
    if nan_strategy == 'drop':
        df = df.dropna()
    elif nan_strategy == 'fill_mean':
        df = df.fillna(df.select_dtypes(include='number').mean())
    elif nan_strategy == 'fill_median':
        df = df.fillna(df.select_dtypes(include='number').median())
    elif nan_strategy == 'fill_mode':
        df = df.fillna(df.mode().iloc[0])
    elif nan_strategy == 'custom' and custom_fills:
        df = df.fillna(custom_fills)
    
    print(f"\nNaN Values After {nan_strategy} Handling:")
    print(df.isna().sum().to_string())
    
    return df

def process_transactions(input_file, output_file, nan_strategy='fill_median'):
    """Full processing pipeline with configurable NaN handling"""
    custom_fills = {
        'CustAccountBalance': 0,
        'CustLocation': 'Unknown',
        'TransactionTime': '00:00:00',
        'CustomerDOB': '1/1/00',
        'CustGender':'X'
    }
    
    df = load_and_clean_data(
        input_file,
        nan_strategy=nan_strategy,
        custom_fills=custom_fills
    )

    
    df.to_csv(output_file, index=False)
    print(f"\nProcessed data saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process transaction data')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('output', help='Output CSV file path')
    parser.add_argument('--nan', choices=['report', 'drop', 'fill_mean', 'fill_median', 'fill_mode', 'custom'],
                       default='fill_median', help='NaN handling strategy')
    args = parser.parse_args()
    
    process_transactions(
        input_file=args.input,
        output_file=args.output,
        nan_strategy=args.nan
    )