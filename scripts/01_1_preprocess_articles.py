#!/usr/bin/env python3
"""
Script to preprocess articles from CSV files.

This script reads CSV files from a directory and consolidates them into a single output file.
Each CSV file contains article information with the following fields:
- apellido: Surname of one of authors of the article
- nombre: Name of one of the authors of the article
- titulo: Title of the article
- resumen: Abstract/summary of the article
- cuil: CUIL identifier
"""

import argparse
import pandas as pd
from pathlib import Path
import sys

from mapa_ciencia_unc.data_handlers import save_output_by_extension


def read_files(articles_path: Path) -> pd.DataFrame:
    """
    Read CSV file from the input directory.

    Args:
        articles_path: Path to articles CSV file

    Returns:
        DataFrame containing all articles from all CSV file
    """
    if not articles_path.exists():
        raise FileNotFoundError(f"Articles file does not exist: {articles_path}")

    print(f"Reading articles file: {articles_path}")

    # Read articles file
    if articles_path.suffix == ".csv":
        df = pd.read_csv(articles_path, sep=";")
    elif articles_path.suffix == ".parquet":
        df = pd.read_parquet(articles_path)
    elif articles_path.suffix == ".json":
        df = pd.read_json(articles_path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {articles_path.suffix}")

    print(f"  - Loaded {len(df)} articles records")
    print(f"  - Columns found: {len(df.columns)}")

    return df


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the dataframe.

    Args:
        df: Dataframe from CSV file

    Returns:
        Preprocessed dataframe
    """
    print("\nPreprocessing data...")

    # Remove duplicates based on all columns except source_file
    initial_count = len(df)
    df = df.drop_duplicates(subset=['apellido', 'nombre', 'titulo', 'resumen', 'cuil'])
    duplicates_removed = initial_count - len(df)

    # Rename columns
    df = df.rename(columns={'cuil': 'cuit'})

    if duplicates_removed > 0:
        print(f"  - Removed {duplicates_removed} duplicate records")

    # Display data summary
    print(f"\nData summary:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Records with missing abstracts: {df['resumen'].isna().sum()}")
    print(f"  - Unique cuits: {df['cuit'].nunique()}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess articles from CSV files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-dir data/raw/ --output-file data/processed/articles.csv
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
        # Read article file
        print("\n" + "=" * 60)
        print("READING ARTICLES DATA")
        print("=" * 60)
        df = read_files(input_dir)


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
