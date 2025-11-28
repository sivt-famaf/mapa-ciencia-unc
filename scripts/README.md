# Scripts Directory

This directory contains data processing and analysis scripts for the UNC Science Map project.

Files follow the established naming convention: `NN_X_descriptive_name.py`
   - `NN`: Sequential number of the preprocessing stage
   - `X`: Sub-step number (if needed)
   - `descriptive_name`: Description of what the script does

# TL;DR

To preprocess the dataset, assuming you have a directory `raw_csv` with the starting data:

```bash
export DATA_DIR=<dirpath>/  # This will only affect this bash session
python scripts/01_1_preprocess_articles.py \
    --input-dir ${DATA_DIR}/raw_csv/articlulos_v2 \
    --output-file ${DATA_DIR}/preprocessed_csv/articles.json \
    > ${DATA_DIR}/preprocessed_csv/articles.log

python scripts/01_2_preprocess_projects_and_calls.py \
    --projects-dir ${DATA_DIR}/raw_csv/proyectos \
    --calls-dir ${DATA_DIR}/raw_csv/convocatorias \
    --output-file ${DATA_DIR}/preprocessed_csv/projects.json \
    > ${DATA_DIR}/preprocessed_csv/projects.log
```

## Scripts Overview

### 01_1_preprocess_articles.py

This script consolidates multiple CSV files containing article information into a single preprocessed dataset. It reads files from a specified directory, validates the data, removes duplicates, and generates a summary report.

```bash
python scripts/01_1_preprocess_articles.py --input-dir <input_directory> --output-file <output_filepath>
```

The script expects a directory containing `.txt` files (which are CSV formatted) with the following structure:

**Input format**
```
input_directory/
├── CENTRO_DE_INVESTIGACION_Y_ESTUDIOS_DE_MATEMATICA.txt
├── ESCUELA_DE_TRABAJO_SOCIAL.txt
└── UNIVERSIDAD_NACIONAL_DE_CORDOBA.txt
```

Each CSV file must contain the following columns:
- `autores`: Authors of the article (string)
- `titulo`: Title of the article (string)
- `resumen`: Abstract/summary of the article (string, may have null values)
- `cuil`: CUIL identifier (integer)
- `lugar_de_trabajo`: Workplace/institution (string)

**Output format**
The script outputs a single consolidated file with all the data from the input files. Supported output formats:
- `.csv`: Comma-separated values
- `.parquet`: Apache Parquet format (recommended for large datasets)
- `.json`: JSON Lines format

The output includes an additional column:
- `source_file`: Name of the source file (without extension) where the record originated

---

### 01_2_preprocess_projects_and_calls.py

This script reads project and call data from two separate directories, concatenates files within each directory, joins them on common identifiers, and outputs a single consolidated dataset.

```bash
python scripts/01_2_preprocess_projects_and_calls.py --projects-dir <projects_directory> --calls-dir <calls_directory> --output-file <output_filepath>
```

The script expects two directories with the following structure:

**Input format**

Projects directory:
```
projects_directory/
├── proyectos_<cuit>.csv
├── proyectos_<cuit>.csv
└── proyectos_<cuit>.csv
```

Calls directory:
```
calls_directory/
├── convocatorias_<cuit>.csv
├── convocatorias_<cuit>.csv
└── convocatorias_<cuit>.csv
```

**Projects CSV columns** (semicolon-separated):
- `convocatoria_id`: Call identifier
- `codigo_tramite`: Transaction code
- `titulo_proyecto`: Project title
- `resumen_proyecto`: Project abstract
- `palabrasclaves`: Keywords
- `rol_grupo`: Group role
- `nombre`: First name
- `apellido`: Last name
- `comision`: Commission
- `tema_periodo`: Period theme
- `tema_periodo_ingles`: Period theme (English)
- `especialidad`: Specialty
- `cuit`: CUIT identifier (extracted from filename)

**Note**: The CUIT for each project is automatically extracted from the filename pattern `proyectos_<cuit>.csv` and added as a new column.

**Calls CSV columns** (semicolon-separated):
- `CUIL`: CUIL identifier (renamed to `cuit`)
- `Cód. Trámite`: Transaction code (renamed to `codigo_tramite`)
- `Fecha Alta`: Registration date
- `Estado Trám.`: Transaction status
- `Convocatoria`: Call name
- `Objeto Evaluación`: Evaluation object
- `Grupo OE`: OE Group
- `Postulante`: Applicant
- `Rol`: Role
- `link`: Link
- `size`: Size
- `tipo_archivo`: File type

**Join condition**: Projects and calls are joined using:
- `df_projects["cuit"]` == `df_calls["cuit"]`
- AND `df_projects["codigo_tramite"]` == `df_calls["codigo_tramite"]`

**Output format**: Same as 01_1 script (supports .csv, .parquet, .json)

**Example**:
```bash
python scripts/01_2_preprocess_projects_and_calls.py \
  --projects-dir data/raw/projects/ \
  --calls-dir data/raw/calls/ \
  --output-file data/processed/projects_calls.parquet
```

---

### 01_3_preprocess_portfolios.py

This script preprocesses portfolio data by reading a CSV file, renaming columns according to a mapping from a JSON file, and saving the result.

**Usage:**
```bash
python scripts/01_3_preprocess_portfolios.py --portfolios-file <portfolio_csv> --output-file <output_filepath>
```

**Arguments:**
- `--portfolios-file`: Path to portfolio CSV file (also supports .parquet, .json)
- `--column-names-file`: (Optional) Path to JSON file with column name mappings (default: `scripts/portfolio_column_names.json`)
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Column Mapping File:**

The script reads column name mappings from a JSON file. The JSON should be a single object where keys are original column names and values are new standardized names:

```json
{
  "CUIL": "cuit",
  "Apellido": "last_name",
  "Nombres": "first_name",
  "Género": "gender",
  "Unidad Académica": "academic_unit",
  ...
}
```

**Processing Steps:**
1. Loads column mapping from JSON file
2. Reads portfolio file (supports CSV, Parquet, JSON)
3. Renames columns according to the mapping
4. Filters to keep only renamed columns (removes any extra columns)
5. Converts CUIT to string type
6. Saves preprocessed data in specified format

**Output format**: Supports .csv, .parquet, .json

**Examples:**

Default usage (uses `scripts/portfolio_column_names.json`):
```bash
python scripts/01_3_preprocess_portfolios.py \
  --portfolios-file data/raw/portfolios.csv \
  --output-file data/processed/portfolios.parquet
```

With custom column mapping file:
```bash
python scripts/01_3_preprocess_portfolios.py \
  --portfolios-file data/raw/portfolios.csv \
  --column-names-file config/custom_portfolio_columns.json \
  --output-file data/processed/portfolios.parquet
```

---

### 02_1_filter_enrolled_users.py

This script filters articles and projects data to include only enrolled users. It performs left joins to keep all enrolled users even if they don't have corresponding articles or projects. The script also cleans HTML-like content from text columns in all output files.

**Usage:**
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file <enrollment_csv> \
  --articles-file <articles_file> \
  --projects-file <projects_file> \
  --sample-size <ratio> \
  --output-directory <output_dir>
```

**Arguments:**
- `--enrollment-file`: Path to enrollment CSV file containing "CUIL (sin guiones)" column
- `--articles-file`: Path to articles data file (supports .csv, .parquet, .json)
- `--projects-file`: Path to projects data file (supports .csv, .parquet, .json)
- `--sample-size`: (Optional) Ratio of enrollment data to use (0.0-1.0, default: 1.0). Use values < 1.0 for sampling/testing
- `--remove-academic-unit`: (Optional) Comma-separated list of academic units to exclude (e.g., "Unit A,Unit B")
- `--output-directory`: Directory where filtered files will be saved

**Processing Steps:**
1. Reads enrollment file and renames "CUIL (sin guiones)" to "cuit"
2. If `--sample-size` < 1.0, randomly samples that fraction of enrollment data
3. If `--remove-academic-unit` is specified, filters out CUITs from those academic units
4. Performs left join: `enrollment LEFT JOIN articles ON cuit`
5. Cleans HTML-like content from article text columns (`titulo`, `resumen`)
6. Saves filtered articles as `articles.json` in output directory
7. Performs left join: `enrollment LEFT JOIN projects ON cuit`
8. Cleans HTML-like content from project text columns (`tema_periodo`, `tema_periodo_ingles`, `titulo_proyecto`, `resumen_proyecto`)
9. Saves filtered projects as `projects.json` in output directory
10. Cleans HTML-like content from enrollment text columns (`research_area`, `last_project_title`)
11. Saves enrollment data as `enrollment.json` in output directory

**Join Behavior:**
- Left joins preserve all enrollment records
- Enrolled users without articles/projects will have NULL values in those fields
- Articles/projects without matching enrollment are excluded

**Text Cleaning:**
The script applies HTML cleaning to remove:
- HTML tags and malformed markup
- LaTeX fragments
- Unicode anomalies
- Reference patterns

This is applied to all text columns in enrollment, articles, and projects data.

**Output Files:**
- `articles.json`: JSON Lines format with enrolled users and their articles (text cleaned)
- `projects.json`: JSON Lines format with enrolled users and their projects (text cleaned)
- `enrollment.json`: JSON Lines format with enrollment data (text cleaned)

**Examples:**

Filter with all enrolled users:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --output-directory data/filtered/
```

Filter with 10% sample for testing:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --sample-size 0.1 \
  --output-directory data/filtered_sample/
```

Filter excluding specific academic units:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --remove-academic-unit "Facultad de Ciencias Exactas,Facultad de Derecho" \
  --output-directory data/filtered/
```

