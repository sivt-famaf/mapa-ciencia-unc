#!/usr/bin/env python3
"""
Script to preprocess portfolio data from CSV files.

This script reads a portfolio CSV file, renames columns according to a mapping,
and saves the result to an output file.
"""

import argparse
import json
import pandas as pd
from pathlib import Path
import sys

from mapa_ciencia_unc.data_handlers import save_output_by_extension


def load_column_mapping(column_names_file: Path) -> dict:
    """
    Load column name mapping from JSON file.

    Args:
        column_names_file: Path to JSON file with column mapping

    Returns:
        Dictionary mapping original column names to new names
    """
    if not column_names_file.exists():
        raise FileNotFoundError(
            f"Column names file does not exist: {column_names_file}"
        )

    print(f"Loading column mapping from: {column_names_file}")

    with open(column_names_file, "r", encoding="utf-8") as f:
        column_mapping = json.load(f)

    print(f"  - Loaded {len(column_mapping)} column mappings")

    return column_mapping


def read_portfolio_file(portfolio_path: Path) -> pd.DataFrame:
    """
    Read portfolio CSV file.

    Args:
        portfolio_path: Path to portfolio CSV file

    Returns:
        DataFrame with portfolio data
    """
    if not portfolio_path.exists():
        raise FileNotFoundError(f"Portfolio file does not exist: {portfolio_path}")

    print(f"Reading portfolio file: {portfolio_path}")

    # Read portfolio file
    if portfolio_path.suffix == ".csv":
        df = pd.read_csv(portfolio_path)
    elif portfolio_path.suffix == ".parquet":
        df = pd.read_parquet(portfolio_path)
    elif portfolio_path.suffix == ".json":
        df = pd.read_json(portfolio_path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {portfolio_path.suffix}")

    print(f"  - Loaded {len(df)} portfolio records")
    print(f"  - Columns found: {len(df.columns)}")

    return df


def preprocess_portfolio(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """
    Preprocess portfolio data by renaming columns.

    Args:
        df: DataFrame with raw portfolio data
        column_mapping: Dictionary mapping original to new column names

    Returns:
        DataFrame with renamed columns
    """
    print("\nPreprocessing portfolio data...")

    # Rename columns
    df = df.rename(columns=column_mapping)

    # Filter to only keep renamed columns (drop any extra columns)
    available_renamed_cols = [
        col for col in column_mapping.values() if col in df.columns
    ]
    df = df[available_renamed_cols]

    print(f"  - Renamed columns from mapping")
    print(f"  - Kept {len(available_renamed_cols)} columns in output")

    # Convert CUIT to string type
    if "cuit" in df.columns:
        df["cuit"] = df["cuit"].astype(str)

    # Display data summary
    print(f"\nData summary:")
    print(f"  - Total records: {len(df)}")
    if "cuit" in df.columns:
        print(f"  - Unique CUITs: {df['cuit'].nunique()}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess portfolio data from CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --portfolios-file data/raw/portfolios.csv --output-file data/processed/portfolios.parquet

  # With custom column mapping file:
  %(prog)s --portfolios-file data/raw/portfolios.csv --column-names-file config/portfolio_columns.json --output-file data/processed/portfolios.parquet
        """,
    )

    parser.add_argument(
        "--portfolios-file",
        type=Path,
        required=True,
        help="Path to portfolio CSV file (also supports .parquet, .json)",
    )

    parser.add_argument(
        "--column-names-file",
        type=Path,
        default=Path("scripts/portfolio_column_names.json"),
        help="Path to JSON file with column name mappings (default: scripts/portfolio_column_names.json)",
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        required=True,
        help="Output filepath for preprocessed data (supports .csv, .parquet, .json)",
    )

    args = parser.parse_args()

    try:
        # Load column mapping
        print("=" * 60)
        print("LOADING COLUMN MAPPING")
        print("=" * 60)
        column_mapping = load_column_mapping(args.column_names_file)

        # Read portfolio file
        print("\n" + "=" * 60)
        print("READING PORTFOLIO DATA")
        print("=" * 60)
        df_portfolio = read_portfolio_file(args.portfolios_file)

        # Preprocess data
        print("\n" + "=" * 60)
        print("PREPROCESSING DATA")
        print("=" * 60)
        df_processed = preprocess_portfolio(df_portfolio, column_mapping)

        # Save output
        print("\n" + "=" * 60)
        print("SAVING OUTPUT")
        print("=" * 60)
        save_output_by_extension(df_processed, args.output_file)

        print("\n" + "=" * 60)
        print("Preprocessing completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
