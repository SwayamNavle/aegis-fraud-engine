#!/usr/bin/env python3
"""
Generate synthetic transaction datasets for Aegis ML training, validation, and demo benchmarking.
Outputs CSV datasets sorted chronologically to avoid future data leakage.
"""

import argparse
import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.producer.producer import SyntheticTransactionGenerator


def generate_dataset(num_records: int = 50000,
                     fraud_ratio: float = 0.015,
                     output_csv: str = "data/raw/train_transactions.csv") -> pd.DataFrame:
    """Generates synthetic dataset chronologically ordered."""
    print(f"[Aegis DataGen] Generating {num_records:,} transactions (Target fraud ratio: {fraud_ratio*100:.2f}%)...")
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    generator = SyntheticTransactionGenerator(num_users=3000, fraud_ratio=fraud_ratio)
    
    base_time = datetime.now(timezone.utc) - timedelta(days=14)
    records = []
    
    for i in range(num_records):
        # Progress time smoothly over 14 days
        progress_secs = (i / max(1, num_records)) * (14 * 86400)
        curr_time = base_time + timedelta(seconds=progress_secs)
        
        event = generator.generate_event(current_time=curr_time)
        records.append(event.model_dump())
        
        if (i + 1) % 10000 == 0:
            print(f"[Aegis DataGen] Generated {i+1:,}/{num_records:,} events...")

    df = pd.DataFrame(records)
    # Ensure chronological sorting
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Save to CSV
    df.to_csv(output_csv, index=False)
    
    fraud_count = df["label"].sum()
    actual_ratio = fraud_count / len(df)
    print(f"[Aegis DataGen] Successfully generated {len(df):,} transactions.")
    print(f"[Aegis DataGen] Legitimate: {len(df)-fraud_count:,} | Fraud: {fraud_count:,} ({actual_ratio*100:.2f}%)")
    print(f"[Aegis DataGen] Saved dataset to: {output_csv}")
    
    # Also save a sample template to data/sample_transactions.csv
    sample_csv = "data/sample_transactions.csv"
    df.head(1000).to_csv(sample_csv, index=False)
    print(f"[Aegis DataGen] Saved sample subset to: {sample_csv}")
    
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Aegis synthetic dataset")
    parser.add_argument("--count", type=int, default=50000, help="Number of records to generate (default 50,000)")
    parser.add_argument("--fraud-ratio", type=float, default=0.015, help="Fraud ratio (default 0.015 = 1.5%)")
    parser.add_argument("--output", type=str, default="data/raw/train_transactions.csv", help="Output CSV path")

    args = parser.parse_args()
    generate_dataset(num_records=args.count, fraud_ratio=args.fraud_ratio, output_csv=args.output)
