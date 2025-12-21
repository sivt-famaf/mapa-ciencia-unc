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

from mapa_ciencia_unc.data_handlers import read_data_file, save_output_by_extension


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
    df = df.drop_duplicates(
        subset=[
            "apellido",
            "nombre",
            "titulo",
            "resumen",
            "cuil",
        ]
    )
    duplicates_removed = initial_count - len(df)

    # Rename columns
    df = df.rename(columns={"cuil": "cuit"})

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
        description="Preprocess articles from CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --articles-file data/raw/ --output-file data/processed/articles.csv
        """,
    )

    parser.add_argument(
        "--articles-file",
        type=Path,
        dest="articles_file",
        help="Alternative way to specify input file",
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        dest="output_file",
        help="Alternative way to specify output file",
    )

    args = parser.parse_args()

    # Handle both positional and flag arguments
    articles_file = args.articles_file
    output_file = args.output_file

    if not articles_file or not output_file:
        parser.error("Both articles_file and output_file are required")

    try:
        # Read article file
        print("\n" + "=" * 60)
        print("READING ARTICLES DATA")
        print("=" * 60)
        print(f"Reading articles file: {articles_file}")
        df = read_data_file(articles_file, separator=";")
        print(f"  - Loaded {len(df)} articles records")
        print(f"  - Columns found: {len(df.columns)}")

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
