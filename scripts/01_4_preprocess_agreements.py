#!/usr/bin/env python3
"""
Script to preprocess agreements data from CSV files.

This script reads a agreements CSV file, and saves the result to an output file.
"""

import argparse
import sys
import pandas as pd
from pathlib import Path

from mapa_ciencia_unc.data_handlers import read_csv_file, save_output_by_extension



def read_agreements_file(agreements_path: Path) -> pd.DataFrame:
    """
    Read agreements CSV file.

    Args:
        agreements_path: Path to agreements CSV file

    Returns:
        DataFrame with agreements data
    """
    if not agreements_path.exists():
        raise FileNotFoundError(f"Agreements file does not exist: {agreements_path}")

    print(f"Reading agreements file: {agreements_path}")

    # Read agreements file
    try:
        # Read CSV with semicolon separator
        df = read_csv_file(agreements_path, separator=";")
    except Exception as e:
        print(f"Error reading {agreements_path.name}: {e}")
    

    print(f"  - Loaded {len(df)} agreements records")
    print(f"  - Columns found: {len(df.columns)}")

    return df


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the combined dataframe.

    Args:
        df: Combined dataframe from all CSV files

    Returns:
        Preprocessed dataframe
    """
    print("\nPreprocessing data...")

    # Remove duplicates based on all columns except source_file
    initial_count = len(df)
    df = df.drop_duplicates()
    duplicates_removed = initial_count - len(df)

    # Rename columns
    df = df.rename(columns={'cuil': 'cuit'})

    if duplicates_removed > 0:
        print(f"  - Removed {duplicates_removed} duplicate records")

    # Display data summary
    print(f"\nData summary:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Records with missing description: {df['descripcion'].isna().sum()}")
    print(f"  - Records with missing type production: {df['tipo_produccion_tecnologica'].isna().sum()}")
    print(f"  - Unique cuits: {df['cuit'].nunique()}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess agreements data from CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-dir data/raw/ --output-file data/processed/agreements.csv
        """
    )

    parser.add_argument(
        '--input-dir',
        type=Path,
        dest='input_dir',
        help='Alternative way to specify input directory'
    )

    parser.add_argument(
        '--output-file',
        type=Path,
        dest='output_file',
        help='Alternative way to specify output file'
    )

    args = parser.parse_args()

    # Handle both positional and flag arguments
    input_dir = args.input_dir
    output_file = args.output_file

    if not input_dir or not output_file:
        parser.error("Both input_dir and output_file are required")

    try:
        # Read portfolio file
        print("\n" + "=" * 60)
        print("READING AGREEMENTS DATA")
        print("=" * 60)
        df = read_agreements_file(input_dir)

        # Preprocess data
        print("\n" + "=" * 60)
        print("PREPROCESSING DATA")
        print("=" * 60)
        df = preprocess_data(df)

        # Save output
        print("\n" + "=" * 60)
        print("SAVING OUTPUT")
        print("=" * 60)
        save_output_by_extension(df, output_file)

        print("\n" + "=" * 60)
        print("Preprocessing completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()