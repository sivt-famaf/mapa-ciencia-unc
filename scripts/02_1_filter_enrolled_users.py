#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to filter articles and projects based on enrolled users.

This script reads an enrollment file containing CUITs of enrolled users,
and filters articles and projects to only include data for those users.
It performs left joins to keep all enrolled users even if they don't have
articles or projects.
"""

import argparse
import random
import pandas as pd
from pathlib import Path
import sys

from mapa_ciencia_unc.data_handlers import clean_html_like


ENROLLMENT_RENAME_COLUMNS = {
    'Dirección de correo electrónico': 'email',
    'Nombres': 'name',
    'Apellidos': 'last_name',
    'CUIL (sin guiones)': 'cuit',
    'Número de ORCID (si posee)': 'orcid_number',
    'Género': 'gender',
    'Unidad Académica': 'academic_unit',
    'Cargo de mayor jerarquía alcanzado': 'highest_position',
    '¿Posee manejo de otros idiomas?': 'languages',
    'Centro de investigación al que pertenece': 'research_center',
    'Breve descripción de su área de investigación': 'research_area',
    'Título del último proyecto de investigación en el que participa tal como fue postulado en SECYT (2023 o 2025)': 'last_project_title',
    'El proyecto está encuadrado en el siguiente ODS:': 'ods',
    'Basándose en la escala de madurez de internacionalización de las y los investigadores, ¿Qué nivel de madurez de internacionalización considera que posee?': 'maturity_level',
    '¿Posee vínculos propios con investigadores del exterior?': 'international_research_links'
}


# TODO move each category to its own variable
TEXT_COLUMNS = [
    # enrollment
    'research_area', 'last_project_title',
    # articles
    'titulo', 'resumen',
    # projects
    'tema_periodo', 'tema_periodo_ingles', 'titulo_proyecto', 'resumen_proyecto',
    # agreements
    'descripcion', 'tipo_produccion_tecnologica'
]


def read_enrollment_file(enrollment_path: Path, sample_size: float) -> pd.DataFrame:
    """
    Read enrollment file and optionally sample it.

    Args:
        enrollment_path: Path to enrollment CSV file
        sample_size: Ratio of data to use (0.0 to 1.0)

    Returns:
        DataFrame with enrollment data
    """
    if not enrollment_path.exists():
        raise FileNotFoundError(f"Enrollment file does not exist: {enrollment_path}")

    print(f"Reading enrollment file: {enrollment_path}")

    # Read enrollment file
    if enrollment_path.suffix == '.csv':
        df = pd.read_csv(enrollment_path)
    elif enrollment_path.suffix == '.parquet':
        df = pd.read_parquet(enrollment_path)
    elif enrollment_path.suffix == '.json':
        df = pd.read_json(enrollment_path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {enrollment_path.suffix}")

    print(f"  - Loaded {len(df)} enrollment records")

    # Rename and filter columns
    df = df.rename(columns=ENROLLMENT_RENAME_COLUMNS)
    df = df[ENROLLMENT_RENAME_COLUMNS.values()]
    if 'cuit' not in df.columns:
        raise ValueError(
            f"Column 'CUIL (sin guiones)' or 'cuit' not found in enrollment file. "
            f"Available columns: {df.columns.tolist()}"
        )

    # Force types
    df = df.astype({'cuit': 'object'})

    # Sample if needed
    if sample_size < 1.0:
        original_size = len(df)
        df = df.sample(frac=sample_size, random_state=42)
        df = df.reset_index(drop=True)
        print(f"  - Sampled {len(df)} records from {original_size} (sample_size={sample_size})")

    return df


def filter_academic_units(df: pd.DataFrame, units_to_remove: list) -> pd.DataFrame:
    """
    Filter out enrollment records from specific academic units.

    Args:
        df: DataFrame with enrollment data
        units_to_remove: List of academic unit names to exclude

    Returns:
        Filtered DataFrame without the specified academic units
    """
    if not units_to_remove:
        return df

    print(f"\nFiltering out academic units...")
    initial_count = len(df)

    # Filter out rows where academic_unit is in the remove list
    df_filtered = df[~df['academic_unit'].isin(units_to_remove)]

    removed_count = initial_count - len(df_filtered)

    print(f"  - Units to remove: {', '.join(units_to_remove)}")
    print(f"  - Records before filtering: {initial_count}")
    print(f"  - Records removed: {removed_count}")
    print(f"  - Records remaining: {len(df_filtered)}")

    return df_filtered


def read_include_cuits_file(include_cuits_path: Path) -> set:
    """
    Read CSV file with CUITs to include.

    Args:
        include_cuits_path: Path to CSV file with 'cuit' column

    Returns:
        Set of CUIT strings to include
    """
    if not include_cuits_path.exists():
        raise FileNotFoundError(f"Include CUITs file does not exist: {include_cuits_path}")

    print(f"Reading include CUITs file: {include_cuits_path}")

    df = pd.read_csv(include_cuits_path)

    if 'cuit' not in df.columns:
        raise ValueError(
            f"Column 'cuit' not found in include CUITs file. "
            f"Available columns: {df.columns.tolist()}"
        )

    cuits = set(df['cuit'].astype(str).unique())
    print(f"  - Loaded {len(cuits)} unique CUITs to include")

    return cuits


def get_combined_cuits(
    df_enrollment: pd.DataFrame,
    df_portfolio: pd.DataFrame = None,
    sample_size: float = 1.0,
    units_to_remove: list = None,
    include_cuits: set = None
) -> set:
    """
    Get combined set of CUITs from enrollment and portfolio data.

    Args:
        df_enrollment: DataFrame with enrollment data
        df_portfolio: Optional DataFrame with portfolio data
        sample_size: Ratio of data to use for sampling
        units_to_remove: List of academic units to exclude
        include_cuits: Optional set of CUITs to include (overrides sampling)

    Returns:
        Set of CUIT strings to include in the final dataset
    """
    print("\nCombining CUITs from enrollment and portfolio...")

    # If include_cuits is provided, use that instead of combining/sampling
    if include_cuits is not None:
        print(f"  - Using provided include CUITs: {len(include_cuits)}")
        combined_cuits = include_cuits
    else:
        # Start with enrollment CUITs
        enrollment_cuits = set(df_enrollment['cuit'].astype(str).unique())
        print(f"  - Enrollment CUITs: {len(enrollment_cuits)}")

        # Add portfolio CUITs if provided
        if df_portfolio is not None:
            portfolio_cuits = set(df_portfolio['cuit'].astype(str).unique())
            print(f"  - Portfolio CUITs: {len(portfolio_cuits)}")
            combined_cuits = enrollment_cuits.union(portfolio_cuits)
            print(f"  - Combined unique CUITs: {len(combined_cuits)}")
        else:
            combined_cuits = enrollment_cuits

        # Apply sampling if needed
        if sample_size < 1.0:
            original_size = len(combined_cuits)
            sample_count = int(len(combined_cuits) * sample_size)
            combined_cuits = set(random.sample(list(combined_cuits), sample_count))
            print(f"  - Sampled {len(combined_cuits)} CUITs from {original_size} (sample_size={sample_size})")

    # Filter by academic unit if needed
    if units_to_remove:
        # Get CUITs to exclude based on academic_unit
        excluded_cuits = set(
            df_enrollment[df_enrollment['academic_unit'].isin(units_to_remove)]['cuit'].astype(str).unique()
        )
        combined_cuits = combined_cuits - excluded_cuits
        print(f"  - Removed {len(excluded_cuits)} CUITs from excluded academic units")
        print(f"  - Final CUITs count: {len(combined_cuits)}")

    return combined_cuits


def read_data_file(file_path: Path, file_type: str) -> pd.DataFrame:
    """
    Read articles, projects or agreements file.

    Args:
        file_path: Path to data file
        file_type: Type of file ("articles", "projects" or "agreements") for logging

    Returns:
        DataFrame with data
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type.capitalize()} file does not exist: {file_path}")

    print(f"Reading {file_type} file: {file_path}")

    # Read file based on extension
    if file_path.suffix == '.csv':
        df = pd.read_csv(file_path)
    elif file_path.suffix == '.parquet':
        df = pd.read_parquet(file_path)
    elif file_path.suffix == '.json':
        df = pd.read_json(file_path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    print(f"  - Loaded {len(df)} {file_type} records")

    # Validate cuit column exists
    if 'cuit' not in df.columns:
        raise ValueError(
            f"Column 'cuit' not found in {file_type} file. "
            f"Available columns: {df.columns.tolist()}"
        )

    # Force type
    df = df.astype({'cuit': 'object'})

    return df


def filter_by_cuit_set(
    cuit_set: set,
    df_data: pd.DataFrame,
    data_type: str
) -> pd.DataFrame:
    """
    Filter data by a set of CUITs.

    Args:
        cuit_set: Set of CUIT strings to include
        df_data: DataFrame with data to filter
        data_type: Type of data for logging

    Returns:
        Filtered DataFrame
    """
    print(f"\nFiltering {data_type} by CUIT set...")

    # Filter to only include CUITs in the set
    df_filtered = df_data[df_data['cuit'].astype(str).isin(cuit_set)]

    print(f"  - {data_type.capitalize()} records before: {len(df_data)}")
    print(f"  - {data_type.capitalize()} records after: {len(df_filtered)}")
    print(f"  - Unique CUITs with {data_type}: {df_filtered['cuit'].nunique()}")

    return df_filtered


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean HTML-like content from text columns.

    Applies the clean_html_like function to all columns specified in TEXT_COLUMNS
    that exist in the dataframe, overriding the original column values.

    Args:
        df: DataFrame to clean

    Returns:
        DataFrame with cleaned text columns
    """
    print("\nCleaning text columns...")

    cleaned_count = 0

    for col in TEXT_COLUMNS:
        if col in df.columns:
            print(f"  - Cleaning column: {col}")
            df[col] = df[col].apply(lambda x: clean_html_like(x) if pd.notna(x) else x)
            cleaned_count += 1

    print(f"  - Cleaned {cleaned_count} text columns")

    return df


def save_output(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save filtered data to output file.

    Args:
        df: DataFrame to save
        output_path: Path where to save the output file
    """
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSON (lines format)
    df.to_json(output_path, orient='records', lines=True)

    print(f"  - Saved to: {output_path}")
    print(f"  - File size: {output_path.stat().st_size / 1024:.2f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Filter articles and projects based on enrolled users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter with all enrolled users:
  %(prog)s --enrollment-file data/enrollment.csv --articles-file data/articles.parquet --projects-file data/projects.parquet --agreements-file data/agreements.csv --output-directory data/filtered/

  # Filter with 10% sample:
  %(prog)s --enrollment-file data/enrollment.csv --articles-file data/articles.parquet --projects-file data/projects.parquet --agreements-file data/agreements.csv --sample-size 0.1 --output-directory data/filtered/
        """
    )
    
    parser.add_argument(
        '--enrollment-file',
        type=Path,
        required=True,
        help='Path to enrollment CSV file with "CUIL (sin guiones)" column'
    )

    parser.add_argument(
        '--articles-file',
        type=Path,
        required=True,
        help='Path to articles data file (CSV, Parquet, or JSON)'
    )

    parser.add_argument(
        '--projects-file',
        type=Path,
        required=True,
        help='Path to projects data file (CSV, Parquet, or JSON)'
    )
    
    parser.add_argument(
        '--agreements-file',
        type=Path,
        required=True,
        help='Path to agreements data file (CSV, Parquet, or JSON)'
    )
    
    parser.add_argument(
        '--portfolios-file',
        type=Path,
        help='(Optional) Path to portfolios data file with "cuit" and "email" columns (CSV, Parquet, or JSON)'
    )

    parser.add_argument(
        '--sample-size',
        type=float,
        default=1.0,
        help='Ratio of enrollment data to use (0.0 to 1.0, default: 1.0). Not compatible with --include-cuits'
    )

    parser.add_argument(
        '--include-cuits',
        type=Path,
        help='Path to CSV file with "cuit" column containing CUITs to include in the sample. Not compatible with --sample-size'
    )

    parser.add_argument(
        '--remove-academic-unit',
        type=str,
        default='',
        help='Comma-separated list of academic units to exclude from results (e.g., "Unit A,Unit B")'
    )

    parser.add_argument(
        '--output-directory',
        type=Path,
        required=True,
        help='Directory where filtered files will be saved'
    )
    
    args = parser.parse_args()
    
    # Validate sample size
    if not 0.0 < args.sample_size <= 1.0:
        parser.error("--sample-size must be between 0.0 and 1.0")

    # Validate that --include-cuits and --sample-size are not used together
    if args.include_cuits and args.sample_size < 1.0:
        parser.error("--include-cuits and --sample-size cannot be used together")
    
    try:
        
        # Read enrollment file (without sampling - we'll do that later with combined CUITs)
        print("=" * 60)
        print("READING ENROLLMENT DATA")
        print("=" * 60)
        df_enrollment = read_enrollment_file(args.enrollment_file, sample_size=1.0)

        # Read portfolio file if provided
        df_portfolio = None
        if args.portfolios_file:
            print("\n" + "=" * 60)
            print("READING PORTFOLIO DATA")
            print("=" * 60)
            df_portfolio = read_data_file(args.portfolios_file, "portfolios")

        # Read include-cuits file if provided
        include_cuits_set = None
        if args.include_cuits:
            print("\n" + "=" * 60)
            print("READING INCLUDE CUITS")
            print("=" * 60)
            include_cuits_set = read_include_cuits_file(args.include_cuits)

        # Get combined CUIT set with sampling and academic unit filtering
        print("\n" + "=" * 60)
        print("CALCULATING CUIT SET")
        print("=" * 60)
        units_to_remove = [unit.strip() for unit in args.remove_academic_unit.split(',') if unit.strip()]
        cuit_set = get_combined_cuits(
            df_enrollment,
            df_portfolio,
            sample_size=args.sample_size,
            units_to_remove=units_to_remove,
            include_cuits=include_cuits_set
        )

        # Filter enrollment by CUIT set
        print("\n" + "=" * 60)
        print("FILTERING ENROLLMENT")
        print("=" * 60)
        df_enrollment = filter_by_cuit_set(cuit_set, df_enrollment, "enrollment")

        # Filter portfolio by CUIT set if provided
        if df_portfolio is not None:
            print("\n" + "=" * 60)
            print("FILTERING PORTFOLIO")
            print("=" * 60)
            df_portfolio = filter_by_cuit_set(cuit_set, df_portfolio, "portfolio")

        # Read articles file
        print("\n" + "=" * 60)
        print("READING ARTICLES DATA")
        print("=" * 60)
        df_articles = read_data_file(args.articles_file, "articles")

        # Read projects file
        print("\n" + "=" * 60)
        print("READING PROJECTS DATA")
        print("=" * 60)
        df_projects = read_data_file(args.projects_file, "projects")
        
        # Read agreements file
        print("\n" + "=" * 60)
        print("READING AGREEMENTS DATA")
        print("=" * 60)
        df_agreements = read_data_file(args.agreements_file, "agreements")
        
        # Filter articles by CUIT set
        print("\n" + "=" * 60)
        print("FILTERING ARTICLES")
        print("=" * 60)
        df_articles_filtered = filter_by_cuit_set(cuit_set, df_articles, "articles")

        # Clean text columns in articles
        print("\n" + "=" * 60)
        print("CLEANING ARTICLES TEXT")
        print("=" * 60)
        df_articles_filtered = clean_text_columns(df_articles_filtered)

        # Save filtered articles
        articles_output = args.output_directory / "articles.json"
        save_output(df_articles_filtered, articles_output)

        # Filter projects by CUIT set
        print("\n" + "=" * 60)
        print("FILTERING PROJECTS")
        print("=" * 60)
        df_projects_filtered = filter_by_cuit_set(cuit_set, df_projects, "projects")

        # Clean text columns in projects
        print("\n" + "=" * 60)
        print("CLEANING PROJECTS TEXT")
        print("=" * 60)
        df_projects_filtered = clean_text_columns(df_projects_filtered)

        # Save filtered projects
        projects_output = args.output_directory / "projects.json"
        save_output(df_projects_filtered, projects_output)
        
        # Filter agreements by CUIT set
        print("\n" + "=" * 60)
        print("FILTERING AGREEMENTS")
        print("=" * 60)
        df_agreements_filtered = filter_by_cuit_set(cuit_set, df_agreements, "agreements")

        # Clean text columns in agreements
        print("\n" + "=" * 60)
        print("CLEANING AGREEMENTS TEXT")
        print("=" * 60)
        df_agreements_filtered = clean_text_columns(df_agreements_filtered)

        # Save filtered agreements
        agreements_output = args.output_directory / "agreements.json"
        save_output(df_agreements_filtered, agreements_output)
        
        # Clean text columns in enrollment
        print("\n" + "=" * 60)
        print("CLEANING ENROLLMENT TEXT")
        print("=" * 60)
        df_enrollment = clean_text_columns(df_enrollment)

        # Save enrollments
        enrollment_output = args.output_directory / "enrollment.json"
        save_output(df_enrollment, enrollment_output)

        # Save portfolio if provided
        if df_portfolio is not None:
            portfolio_output = args.output_directory / "portfolios.json"
            save_output(df_portfolio, portfolio_output)

        print("\n" + "=" * 60)
        print("FILTERING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nOutput files:")
        print(f"  - {articles_output}")
        print(f"  - {projects_output}")
        print(f"  - {enrollment_output}")
        if df_portfolio is not None:
            print(f"  - {portfolio_output}")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
