#!/usr/bin/env python3
"""
Script to preprocess projects and calls data from CSV files.

This script reads CSV files from two separate directories (projects and calls),
concatenates files within each directory, joins them on common fields,
and saves the result to an output file.

Projects and calls are joined using:
- df_projects["cuit"] == df_calls["cuit"]
- df_projects["codigo_tramite"] == df_calls["codigo_tramite"]
"""

import argparse
import pandas as pd
from pathlib import Path
import sys

from mapa_ciencia_unc.data_handlers import read_csv_file


COLUMN_RENAMES = {
    'CUIL': 'cuit',
    'CÃ³d. TrÃ¡mite': 'codigo_tramite',
    'Fecha Alta': 'fecha_alta',
    'Estado TrÃ¡m.': 'estado_tramie',
    'Convocatoria': 'convocatoria',
    'Objeto EvaluaciÃ³n': 'objeto_evaluacion',
    'Grupo OE': 'grupo_oe',
    'Postulante': 'postulante',
    'Rol': 'rol',
}


def read_calls_directory(calls_dir: Path) -> pd.DataFrame:
    """
    Read all calls CSV files from the directory and concatenate them.

    Args:
        calls_dir: Path to directory containing calls CSV files

    Returns:
        DataFrame containing all calls data

    Expected columns:
        CUIL, Cód. Trámite, Fecha Alta, Estado Trám., Convocatoria,
        Objeto Evaluación, Grupo OE, Postulante, Rol, link, size, tipo_archivo
    """
    if not calls_dir.exists():
        raise FileNotFoundError(f"Calls directory does not exist: {calls_dir}")

    if not calls_dir.is_dir():
        raise NotADirectoryError(f"Calls path is not a directory: {calls_dir}")

    # Find all convocatorias CSV files
    csv_files = list(calls_dir.glob("convocatorias_*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No convocatorias_*.csv files found in: {calls_dir}")

    print(f"Found {len(csv_files)} calls files to process")

    dataframes = []

    for csv_file in csv_files:
        try:
            # Read CSV with semicolon separator
            df = read_csv_file(csv_file, separator=';')
            dataframes.append(df)
        except Exception as e:
            print(f"Error reading {csv_file.name}: {e}")
            continue

    if not dataframes:
        raise ValueError("No calls data was successfully loaded from any files")

    # Concatenate all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Rename columns and filter out unused columns
    combined_df = combined_df.rename(columns=COLUMN_RENAMES)
    combined_df = combined_df[COLUMN_RENAMES.values()]
    print(f"\nTotal calls records loaded: {len(combined_df)}")

    return combined_df


def read_projects_directory(projects_dir: Path) -> pd.DataFrame:
    """
    Read all projects CSV files from the directory and concatenate them.

    Args:
        projects_dir: Path to directory containing projects CSV files

    Returns:
        DataFrame containing all projects data

    Expected columns:
        convocatoria_id, codigo_tramite, titulo_proyecto, resumen_proyecto,
        palabrasclaves, rol_grupo, nombre, apellido, comision, tema_periodo,
        tema_periodo_ingles, especialidad
    """
    if not projects_dir.exists():
        raise FileNotFoundError(f"Projects directory does not exist: {projects_dir}")

    if not projects_dir.is_dir():
        raise NotADirectoryError(f"Projects path is not a directory: {projects_dir}")

    # Find all proyectos CSV files
    csv_files = list(projects_dir.glob("proyectos_*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No proyectos_*.csv files found in: {projects_dir}")

    print(f"Found {len(csv_files)} projects files to process")

    dataframes = []

    for csv_file in csv_files:
        try:
            # Extract CUIT from filename (format: proyectos_<cuit>.csv)
            filename = csv_file.stem  # Get filename without extension
            cuit = filename.replace('proyectos_', '')
            # Read CSV with semicolon separator
            df = read_csv_file(csv_file, separator=';')
            # Add CUIT column extracted from filename
            df['cuit'] = cuit
            dataframes.append(df)
        except Exception as e:
            print(f"Error reading {csv_file.name}: {e}")
            continue

    if not dataframes:
        raise ValueError("No projects data was successfully loaded from any files")

    # Concatenate all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    print(f"\nTotal projects records loaded: {len(combined_df)}")

    return combined_df


def join_dataframes(df_calls: pd.DataFrame, df_projects: pd.DataFrame) -> pd.DataFrame:
    """
    Join calls and projects dataframes.

    Args:
        df_calls: DataFrame containing calls data
        df_projects: DataFrame containing projects data

    Returns:
        Joined DataFrame

    Join condition:
        df_projects["cuit"] == df_calls["cuit"]
        AND df_projects["codigo_tramite"] == df_calls["codigo_tramite"]
    """
    print("\nJoining dataframes...")

    # Validate that join columns exist in calls dataframe
    if "cuit" not in df_calls.columns:
        raise ValueError(f"'cuit' column not found in calls data. Available columns: {df_calls.columns.tolist()}")

    if "codigo_tramite" not in df_calls.columns:
        raise ValueError(f"'codigo_tramite' column not found in calls data. Available columns: {df_calls.columns.tolist()}")

    # Validate that join columns exist in projects dataframe
    if "cuit" not in df_projects.columns:
        raise ValueError(f"'cuit' column not found in projects data. Available columns: {df_projects.columns.tolist()}")

    if "codigo_tramite" not in df_projects.columns:
        raise ValueError(f"'codigo_tramite' column not found in projects data. Available columns: {df_projects.columns.tolist()}")

    # Perform the join on both CUIT and codigo_tramite
    df_joined = pd.merge(
        df_projects,
        df_calls,
        on=["cuit", "codigo_tramite"],
        how="inner"
    )

    print(f"  - Projects records: {len(df_projects)}")
    print(f"  - Calls records: {len(df_calls)}")
    print(f"  - Joined records: {len(df_joined)}")

    # Calculate unmatched records
    projects_key = df_projects['cuit'].astype(str) + '_' + df_projects['codigo_tramite'].astype(str)
    calls_key = df_calls['cuit'].astype(str) + '_' + df_calls['codigo_tramite'].astype(str)

    print(f"  - Projects without matching calls: {len(df_projects) - projects_key.isin(calls_key).sum()}")
    print(f"  - Calls without matching projects: {len(df_calls) - calls_key.isin(projects_key).sum()}")

    return df_joined


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the joined dataframe.

    Args:
        df: Joined dataframe

    Returns:
        Preprocessed dataframe
    """
    print("\nPreprocessing data...")

    # Remove duplicates
    initial_count = len(df)
    df = df.drop_duplicates()
    duplicates_removed = initial_count - len(df)

    if duplicates_removed > 0:
        print(f"  - Removed {duplicates_removed} duplicate records")

    # Display data summary
    print(f"\nData summary:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Unique CUITs: {df['cuit'].nunique()}")
    if 'codigo_tramite' in df.columns:
        print(f"  - Unique transactions (codigo_tramite): {df['codigo_tramite'].nunique()}")

    # Check for missing values in key columns
    if 'titulo_proyecto' in df.columns:
        print(f"  - Projects with missing titles: {df['titulo_proyecto'].isna().sum()}")
    if 'resumen_proyecto' in df.columns:
        print(f"  - Projects with missing abstracts: {df['resumen_proyecto'].isna().sum()}")

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
        description="Preprocess projects and calls from CSV files in two directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --projects-dir data/raw/projects/ --calls-dir data/raw/calls/ --output-file data/processed/projects_calls.parquet
        """
    )

    parser.add_argument(
        '--projects-dir',
        type=Path,
        required=True,
        help='Directory containing proyectos_*.csv files'
    )

    parser.add_argument(
        '--calls-dir',
        type=Path,
        required=True,
        help='Directory containing convocatorias_*.csv files'
    )

    parser.add_argument(
        '--output-file',
        type=Path,
        required=True,
        help='Output filepath for preprocessed data (supports .csv, .parquet, .json)'
    )

    args = parser.parse_args()

    try:
        # Read calls data
        print("=" * 60)
        print("READING CALLS DATA")
        print("=" * 60)
        df_calls = read_calls_directory(args.calls_dir)

        # Read projects data
        print("\n" + "=" * 60)
        print("READING PROJECTS DATA")
        print("=" * 60)
        df_projects = read_projects_directory(args.projects_dir)

        # Join dataframes
        print("\n" + "=" * 60)
        print("JOINING DATA")
        print("=" * 60)
        df_joined = join_dataframes(df_calls, df_projects)

        # Preprocess data
        df_processed = preprocess_data(df_joined)

        # Save output
        save_output(df_processed, args.output_file)

        print("\n" + "=" * 60)
        print("Preprocessing completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
