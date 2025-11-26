#!/usr/bin/env python3
"""
Script to filter articles and projects based on enrolled users.

This script reads an enrollment file containing CUITs of enrolled users,
and filters articles and projects to only include data for those users.
It performs left joins to keep all enrolled users even if they don't have
articles or projects.
"""

import argparse
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
    'tema_periodo', 'tema_periodo_ingles', 'titulo_proyecto', 'resumen_proyecto'
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


def read_data_file(file_path: Path, file_type: str) -> pd.DataFrame:
    """
    Read articles or projects file.

    Args:
        file_path: Path to data file
        file_type: Type of file ("articles" or "projects") for logging

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


def filter_by_enrollment(
    df_enrollment: pd.DataFrame,
    df_data: pd.DataFrame,
    data_type: str
) -> pd.DataFrame:
    """
    Perform left join of enrollment with data (articles or projects).

    Args:
        df_enrollment: DataFrame with enrollment data
        df_data: DataFrame with articles or projects data
        data_type: Type of data ("articles" or "projects") for logging

    Returns:
        Filtered DataFrame with all enrollment records
    """
    print(f"\nFiltering {data_type} by enrollment...")

    # Perform left join: keep all enrollment records
    # I need to do this instead of a merge because of some problem with the
    # type of the cuit column
    enrolled_cuits = set(df_enrollment.cuit.apply(lambda x: str(x)).values)
    shared_cuits = [x for x in df_data.cuit if str(x) in enrolled_cuits]
    df_filtered = df_data[df_data.cuit.isin(shared_cuits)]

    print(f"  - Enrollment records: {len(df_enrollment)}")
    print(f"  - {data_type.capitalize()} records: {len(df_data)}")
    print(f"  - Filtered records (after left join): {len(df_filtered)}")

    # Count how many enrolled users have data
    users_with_data = len(df_filtered.cuit.unique())
    users_without_data = len(df_enrollment) - users_with_data

    print(f"  - Enrolled users with {data_type}: {users_with_data}")
    print(f"  - Enrolled users without {data_type}: {users_without_data}")

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
  %(prog)s --enrollment-file data/enrollment.csv --articles-file data/articles.parquet --projects-file data/projects.parquet --output-directory data/filtered/

  # Filter with 10% sample:
  %(prog)s --enrollment-file data/enrollment.csv --articles-file data/articles.parquet --projects-file data/projects.parquet --sample-size 0.1 --output-directory data/filtered/
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
        '--sample-size',
        type=float,
        default=1.0,
        help='Ratio of enrollment data to use (0.0 to 1.0, default: 1.0)'
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

    try:
        # Read enrollment file
        print("=" * 60)
        print("READING ENROLLMENT DATA")
        print("=" * 60)
        df_enrollment = read_enrollment_file(args.enrollment_file, args.sample_size)

        # Filter academic units if specified
        units_to_remove = [unit.strip() for unit in args.remove_academic_unit.split(',') if unit.strip()]
        if units_to_remove:
            print("\n" + "=" * 60)
            print("FILTERING ACADEMIC UNITS")
            print("=" * 60)
            df_enrollment = filter_academic_units(df_enrollment, units_to_remove)

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

        # Filter articles by enrollment
        print("\n" + "=" * 60)
        print("FILTERING ARTICLES")
        print("=" * 60)
        df_articles_filtered = filter_by_enrollment(df_enrollment, df_articles, "articles")

        # Clean text columns in articles
        print("\n" + "=" * 60)
        print("CLEANING ARTICLES TEXT")
        print("=" * 60)
        df_articles_filtered = clean_text_columns(df_articles_filtered)

        # Save filtered articles
        articles_output = args.output_directory / "articles.json"
        save_output(df_articles_filtered, articles_output)

        # Filter projects by enrollment
        print("\n" + "=" * 60)
        print("FILTERING PROJECTS")
        print("=" * 60)
        df_projects_filtered = filter_by_enrollment(df_enrollment, df_projects, "projects")

        # Clean text columns in projects
        print("\n" + "=" * 60)
        print("CLEANING PROJECTS TEXT")
        print("=" * 60)
        df_projects_filtered = clean_text_columns(df_projects_filtered)

        # Save filtered projects
        projects_output = args.output_directory / "projects.json"
        save_output(df_projects_filtered, projects_output)

        # Clean text columns in enrollment
        print("\n" + "=" * 60)
        print("CLEANING ENROLLMENT TEXT")
        print("=" * 60)
        df_enrollment = clean_text_columns(df_enrollment)

        # Save enrollments
        enrollment_output = args.output_directory / "enrollment.json"
        save_output(df_enrollment, enrollment_output)

        print("\n" + "=" * 60)
        print("FILTERING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nOutput files:")
        print(f"  - {articles_output}")
        print(f"  - {projects_output}")
        print(f"  - {enrollment_output}")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
