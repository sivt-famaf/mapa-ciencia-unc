#!/usr/bin/env python3
"""
Script to preprocess articles from CSV files.

This script reads CSV files from a directory and consolidates them into a single output file.
Each CSV file contains article information with the following fields:
- autores: Authors of the article
- titulo: Title of the article
- resumen: Abstract/summary of the article
- cuil: CUIL identifier
- lugar_de_trabajo: Workplace/institution
"""

import argparse
import pandas as pd
from pathlib import Path
import sys

from mapa_ciencia_unc.data_handlers import read_csv_file


def read_csv_files(input_dir: Path) -> pd.DataFrame:
    """
    Read all CSV files from the input directory and concatenate them.

    Args:
        input_dir: Path to directory containing CSV files

    Returns:
        DataFrame containing all articles from all CSV files
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    # Find all .txt files (which are actually CSVs based on the structure)
    csv_files = list(input_dir.glob("*.txt"))

    if not csv_files:
        raise FileNotFoundError(f"No .txt files found in directory: {input_dir}")

    print(f"Found {len(csv_files)} files to process")

    dataframes = []

    for csv_file in csv_files:
        print(f"Reading {csv_file.name}...")
        try:
            df = read_csv_file(csv_file)

            dataframes.append(df)
            print(f"  - Loaded {len(df)} records")

        except Exception as e:
            print(f"Error reading {csv_file.name}: {e}")
            continue

    if not dataframes:
        raise ValueError("No data was successfully loaded from any files")

    # Concatenate all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    print(f"\nTotal records loaded: {len(combined_df)}")

    return combined_df


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
    df = df.drop_duplicates(subset=['autores', 'titulo', 'resumen', 'cuil', 'lugar_de_trabajo'])
    duplicates_removed = initial_count - len(df)

    if duplicates_removed > 0:
        print(f"  - Removed {duplicates_removed} duplicate records")

    # Display data summary
    print(f"\nData summary:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Records with missing abstracts: {df['resumen'].isna().sum()}")
    print(f"  - Unique authors: {df['autores'].nunique()}")
    print(f"  - Unique workplaces: {df['lugar_de_trabajo'].nunique()}")

    return df


def save_output(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save the preprocessed data to the output file.

    Args:
        df: Preprocessed dataframe
        output_path: Path where to save the output file
    """
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine output format based on file extension
    if output_path.suffix == '.csv':
        df.to_csv(output_path, index=False)
    elif output_path.suffix == '.parquet':
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == '.json':
        df.to_json(output_path, orient='records', lines=True)
    else:
        # Default to CSV
        df.to_csv(output_path, index=False)

    print(f"\nOutput saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")


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
        df = read_csv_files(input_dir)
        df = preprocess_data(df)
        save_output(df, output_file)

        print("\nPreprocessing completed successfully!")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
