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
    --output-file ${DATA_DIR}/1_preprocessed_csv/articles.json \
    > ${DATA_DIR}/1_preprocessed_csv/articles.log

python scripts/01_2_preprocess_projects_and_calls.py \
    --projects-dir ${DATA_DIR}/raw_csv/proyectos \
    --calls-dir ${DATA_DIR}/raw_csv/convocatorias \
    --output-file ${DATA_DIR}/1_preprocessed_csv/projects.json \
    > ${DATA_DIR}/1_preprocessed_csv/projects.log

python scripts/01_3_preprocess_portfolios.py \
  --portfolios-file ${DATA_DIR}/raw_csv/portfolios.csv \
  --output-file ${DATA_DIR}/1_preprocessed_csv/portfolios.json \
    > ${DATA_DIR}/1_preprocessed_csv/portfolios.log

python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file ${DATA_DIR}/0_raw_csv/empadronamientos.csv \
  --portfolios-file ${DATA_DIR}/1_preprocessed_csv/portfolios.json \
  --articles-file ${DATA_DIR}/1_preprocessed_csv/articles.json \
  --projects-file ${DATA_DIR}/1_preprocessed_csv/projects.json \
  --remove-academic-unit "FD" \
  --output-directory ${DATA_DIR}/2_merged_sampled_data \
  --include-cuits ${DATA_DIR}/raw_pdfs/cuit_list_sample_30.csv \
  > ${DATA_DIR}/2_merged_data/merge_logs.log
```

## Scripts Overview

### 01_1_preprocess_articles.py

This script preprocesses articles data by reading a CSV file and saving the result.

**Usage:**
```bash
python scripts/01_1_preprocess_articles.py --articles-file <articles_csv> --output-file <output_filepath>
```

**Arguments:**
- `--articles-file`: Path to articles CSV file (also supports .parquet, .json)
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Reads article file
2. Filters to keep only renamed columns (removes any extra columns)
3. Converts CUIT to string type
4. Saves preprocessed data in specified format

**Output format**: Supports .csv, .parquet, .json

**Examples:**
```bash
python scripts/01_1_preprocess_articles.py \
  --articles-file data/raw/articles.csv \
  --output-file data/processed/articles.parquet
```

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
### 01_4_preprocess_agreements.py

This script preprocesses agreements data by reading a CSV file and saving the result.


**Usage:**
```bash
python scripts/01_4_preprocess_agreements.py --agreements-file <agreement_csv> --output-file <output_filepath>
```

**Arguments:**
- `--agreements-file`: Path to agreement CSV file
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Reads agreement file
2. Filters to keep only renamed columns (removes any extra columns)
3. Converts CUIT to string type
4. Saves preprocessed data in specified format

**Output format**: Supports .csv, .parquet, .json

**Examples:**
```bash
python scripts/01_4_preprocess_agreements.py \
  --agreements-file data/raw/agreements.csv \
  --output-file data/processed/agreements.parquet
```

---

### 02_1_filter_enrolled_users.py

This script filters articles, projects, agreements and optionally portfolios based on a combined set of CUITs from enrollment and portfolio data. It applies sampling and academic unit filtering to the combined CUIT set, then filters all datasets accordingly. The script also cleans HTML-like content from text columns in all output files.

**Usage:**
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file <enrollment_csv> \
  --articles-file <articles_file> \
  --projects-file <projects_file> \
  --agreements-file <agreements_file> \
  --portfolios-file <portfolios_file> \
  --sample-size <ratio> \
  --output-directory <output_dir>
```

**Arguments:**
- `--enrollment-file`: Path to enrollment CSV file containing "CUIL (sin guiones)" column
- `--articles-file`: Path to articles data file (supports .csv, .parquet, .json)
- `--projects-file`: Path to projects data file (supports .csv, .parquet, .json)
- `--agreements-file`: Path to agreements CSV file
- `--portfolios-file`: (Optional) Path to portfolios data file with "cuit" and "email" columns
- `--sample-size`: (Optional) Ratio of combined CUIT data to use (0.0-1.0, default: 1.0). Not compatible with `--include-cuits`
- `--include-cuits`: (Optional) Path to CSV file with "cuit" column containing specific CUITs to include. Not compatible with `--sample-size`
- `--remove-academic-unit`: (Optional) Comma-separated list of academic units to exclude
- `--output-directory`: Directory where filtered files will be saved

**Processing Steps:**
1. Reads enrollment file and renames "CUIL (sin guiones)" to "cuit"
2. Reads portfolios file if provided
3. Reads include-cuits file if provided
4. Determines the CUIT set to use:
   - If `--include-cuits` is provided, uses those CUITs (ignores `--sample-size`)
   - Otherwise, combines CUITs from enrollment and portfolios into a single set
   - If `--sample-size` < 1.0, randomly samples that fraction of combined CUITs
5. If `--remove-academic-unit` is specified, removes CUITs from those academic units
6. Filters enrollment, portfolios, articles, projects, and agreements by the final CUIT set
7. Cleans HTML-like content from all text columns
8. Saves all filtered datasets as JSON files

**Output Files:**
- `articles.json`: Filtered articles (text cleaned)
- `projects.json`: Filtered projects (text cleaned)
- `enrollment.json`: Filtered enrollment data (text cleaned)
- `agreements.json`: Filtered agreements (text cleaned)
- `portfolios.json`: Filtered portfolios (only if `--portfolios-file` was provided)

**Filtering Behavior:**
- All datasets are filtered to include only CUITs in the final CUIT set
- The CUIT set is the union of enrollment and portfolio CUITs
- Sampling and academic unit filtering apply to the combined CUIT set
- All output datasets will have consistent CUITs

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
- `agreements.json`: JSON Lines format with enrolled users and their agreements (text cleaned)

**Examples:**

Filter with all enrolled users:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --agreements-file data/processed/agreements.csv \
  --output-directory data/filtered/
```

Filter with 10% sample for testing:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --agreements-file data/processed/agreements.csv \
  --sample-size 0.1 \
  --output-directory data/filtered_sample/
```

Filter excluding specific academic units:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --agreements-file data/processed/agreements.csv \
  --remove-academic-unit "Facultad de Ciencias Exactas,Facultad de Derecho" \
  --output-directory data/filtered/
```

Filter with specific list of CUITs:
```bash
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file data/enrollment.csv \
  --articles-file data/processed/articles.parquet \
  --projects-file data/processed/projects_calls.parquet \
  --agreements-file data/processed/agreements.csv \
  --include-cuits data/selected_cuits.csv \
  --output-directory data/filtered/
```

### 03_01_upload_sample_to_db.py
Script to upload the sample .json files to the database.

Files to upload:
- articles.json
- projects.json
- enrollments.json

Steps, for each file:
1. Read the JSON file.
2. Parse the JSON data into the corresponding data formats (i.e. language str -> list[str])
3. Use the api endpoints to upload the data to the database in batches to avoid overloading the server.

Inputs:
    - Username and password for API authentication.
    - API base URL.
    - Path to the json files directory.

    
Format guidelines for the json files:
Each json file is expected to have one JSON object per line, in the following formats:
Article Format example:
    {
        "autores": "string1; string2; string3",
        "titulo": "string",
        "resumen": "string",
        "cuit": "12341234123",
        "lugar_de_trabajo": "string"
    }

Project Format example:
    {
        "convocatoria_id": 123123123,
        "codigo_tramite": "12312312312312CB",
        "titulo_proyecto": "string",
        "resumen_proyecto": "string",
        "palabrasclaves": "string1; string2; string3",
        "rol_grupo": "string",
        "nombre": "string",
        "apellido": "string",
        "comision": "string",
        "tema_periodo": "string",
        "tema_periodo_ingles": "string",
        "especialidad": null,
        "cuit": 12341234123,
        "fecha_alta": "2012-02-23 18:42:44",
        "estado_tramie": "string",
        "convocatoria": "string",
        "objeto_evaluacion": "string",
        "grupo_oe": "string",
        "postulante": "string",
        "rol": "string"
    }

Enrollment Format example:
    {
        "email": "example@domain.com",
        "name": "string",
        "last_name": "string",
        "cuit": 12341234123,
        "orcid_number": "0000-0001-0002-0003",
        "gender": "string",
        "academic_unit": "string1,string2,string3",
        "highest_position": "string",
        "languages": "string1,string2,string3",
        "research_center": "string",
        "research_area": "string",
        "last_project_title": "string",
        "ods": "string1,string2,string3",
        "maturity_level": "string",
        "international_research_links": "string"
    }

Example usage:
```
python scripts/03_01_upload_sample_to_db.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8123 \
    --samples-dir path/to/samples
```

### 04_01_upload_sample_to_db.py
This process flattens the nested project file structure by moving all files from subdirectories
to a single target directory. It searches through each subdirectory recursively and
attempts to find a descriptive file for each project, it will look for files in the following order:
1. File containting the word 'plan' in its name. (plan de trabajo)
2. File containting the word 'fundamentac' in its name. (fundamentación)
3. File containting the word 'justific' in its name. (justificación)
4. File containting the word 'proy_a_desarrollar' in its name. (proyecto a desarrollar)

It renames files to the following format:
<cuil>_<codigo_tramite>_<original_filename>.<extension>

These extensions are considered valid: '.pdf', '.doc', '.docx', '.rtf', '.odt', '.rar'

If no descriptive file is found, it will skip that project.
It does not avoid duplicate files.

Inputs:
 - A source directory with nested subdirectories.

Outputs:
 - A target directory with all files flattened. Will create the target directory if it does not exist

Example usage:
```
python scripts/04_01_flatten_project_file_structure.py \
    --source-dir path/to/nested/projects \
    --target-dir path/to/flattened/projects
```

### 04_02_extract_intro_from_project_files.py
This process attempts to open all files in a given directory and extract the introductory text
from each project file. It saves the extracted intros into a json file for further use.

By default, 500 are extracted from each file.
These extensions are considered valid: '.pdf', '.doc', '.docx', '.rtf', '.odt', '.rar'
If a file cannot be opened or no intro can be extracted, it will skip that file.
Inputs:
    - A source directory with project files.
Outputs:
    - A json file with the extracted intros, where keys are the file names and values are the extracted text.

Example usage:
```
python scripts/04_02_extract_intro_from_project_files.py \
    --source-dir path/to/project/files \
    --output-file path/to/output/intros.json \
    --num-words 500
```
Requires:
  
  python packages:
    - pymupdf (https://pymupdf.readthedocs.io/en/latest/)
    - python-docx (https://python-docx.readthedocs.io/en/latest/)
    - striprtf (https://pypi.org/project/striprtf/)
    - odf (https://pypi.org/project/odfpy/)
    - rarfile (https://rarfile.readthedocs.io/#)
  
  system packages:
    - antiword (for .doc files)
    - unrar/unar/7zip/p7zip (backend for rarfile https://rarfile.readthedocs.io/#)

### 04_03_upload_projects_to_db.py
This process uploads projects texts from a json file to the database.
The json file should be the ouput of the script 04_02_extract_intro_from_project_files.py

Inputs:
    - A json file with project texts. The json keys are expected to be "<cuit>_<codigo_tramite>_<filename>"
    - The API url to upload the data to.
    - Username and password for API authentication.
    - Overwrite flag to indicate whether to overwrite existing entries in the database. (based on cuit and codigo_tramite)

Example usage:
```
python scripts/04_03_upload_projects_to_db.py \
    --input-file path/to/project_texts.json \
    --api-url http://example.com \
    --username admin \
    --password secret \
    --overwrite
```