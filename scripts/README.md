# Scripts Directory

This directory contains data processing and analysis scripts for the UNC Science Map project.
These scripts may not match exactly your data and need some tweaking before using.

## Naming Convention

Files follow the established naming convention: `NN_X_descriptive_name.py`
   - `NN`: Sequential number of the preprocessing stage
   - `X`: Sub-step number (if needed)
   - `descriptive_name`: Description of what the script does

## Data Processing Pipeline

The scripts implement a multi-stage pipeline to transform raw data into a clean database:

### Stage 01: Preprocessing (`01_*` scripts → `raw_csv/` to `preprocessed_csv/`)

**Purpose**: Transform raw CSV files into clean, standardized data with normalized column names and formats.

**What preprocessing does**:
- **Column renaming**: Uses JSON mapping files to standardize column names (Spanish → English)
- **Format conversion**: Reads CSV/Parquet/JSON, outputs to any format
- **Data normalization**: Converts CUIT to string, handles missing values, removes duplicates
- **Encoding handling**: Automatically detects encodings (UTF-8, Latin-1, CP1252)
- **Type conversion**: Ensures consistent data types across fields

**Scripts**:
- `01_1_preprocess_portfolios.py` - Portfolio/researcher profile data
- `01_2_preprocess_enrollments.py` - Enrollment/registration data
- `01_3_preprocess_articles.py` - Publication/article data
- `01_4_preprocess_agreements.py` - Institutional agreements data

**Output**: Clean files with standardized schemas in `preprocessed_csv/`

### Stage 02: Filtering & Merging (`02_*` scripts → `preprocessed_csv/` to `merged_data/`)

**Purpose**: Combine preprocessed files, filter by enrolled users, and clean text content.

**What merging does**:
- Filters all data to only include enrolled researchers (by CUIT)
- Cleans HTML tags, LaTeX fragments, and unicode anomalies from text fields
- Applies sampling for testing (optional)
- Filters by academic unit (optional)
- Ensures consistent CUIT identifiers across all datasets

**Output**: Merged, filtered, text-cleaned files ready for database upload

### Stage 03: Database Upload (`03_*` scripts → `merged_data/` to MongoDB)

**Purpose**: Batch-upload processed data to MongoDB via the API.

The web application reads directly from MongoDB to display researchers, articles, projects, etc.

### Stage 04: Project Files (Optional, `04_*` scripts)

**Purpose**: Extract and upload detailed project descriptions from PDF/DOC files.

Adds rich text content to supplement project metadata.

### Stage 05: Bulk upload (Optional, `05_*` scripts)

**Purpose**: Upload in bulk embeddings and summaries generated with
other tools to the db.

Allows for specification of tags and model used during creation


---

## Entity Types

The webapp handles different kinds of entities:

- **Articles** - Publication data (authors, titles, abstracts, CUIT identifiers)
- **Projects** - Research project information and funding calls
- **Portfolios** - Researcher profile information
- **Agreements** - Institutional agreements data
- **Enrollments** - Researcher enrollment and affiliation data
- **Project Files** - PDF/DOC/DOCX files with detailed project descriptions

- **Summaries** - Researcher data processed and condensed into text
- **Embeddings** - Vector representing researchers and research areas

---

# Quick Start

To preprocess the dataset, assuming you have a directory `raw_csv` with the starting data:

```bash
export DATA_DIR=<dirpath>  # This will only affect this bash session

# Stage 01: Preprocess raw CSV files
python scripts/01_1_preprocess_portfolios.py \
  --portfolios-file ${DATA_DIR}/raw_csv/portfolios.csv \
  --output-file ${DATA_DIR}/preprocessed_csv/portfolios.json \
  > ${DATA_DIR}/preprocessed_csv/portfolios.log

python scripts/01_2_preprocess_enrollments.py \
  --enrollments-file ${DATA_DIR}/raw_csv/enrollments.csv \
  --output-file ${DATA_DIR}/preprocessed_csv/enrollments.json \
  > ${DATA_DIR}/preprocessed_csv/enrollments.log

python scripts/01_3_preprocess_articles.py \
  --articles-file ${DATA_DIR}/raw_csv/articles.csv \
  --output-file ${DATA_DIR}/preprocessed_csv/articles.json \
  > ${DATA_DIR}/preprocessed_csv/articles.log

python scripts/01_4_preprocess_agreements.py \
  --agreements-file ${DATA_DIR}/raw_csv/agreements.csv \
  --output-file ${DATA_DIR}/preprocessed_csv/agreements.json \
  > ${DATA_DIR}/preprocessed_csv/agreements.log

python scripts/01_5_preprocess_projects_and_calls.py \
  --projects-dir ${DATA_DIR}/raw_csv/proyectos \
  --calls-dir ${DATA_DIR}/raw_csv/convocatorias \
  --output-file ${DATA_DIR}/preprocessed_csv/calls.json \
  > ${DATA_DIR}/preprocessed_csv/calls.log

# Stage 02: Filter by enrolled users and merge
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file ${DATA_DIR}/preprocessed_csv/enrollments.json \
  --portfolios-file ${DATA_DIR}/preprocessed_csv/portfolios.json \
  --articles-file ${DATA_DIR}/preprocessed_csv/articles.json \
  --projects-file ${DATA_DIR}/preprocessed_csv/calls.json \
  --agreements-file ${DATA_DIR}/preprocessed_csv/agreements.json \
  --output-directory ${DATA_DIR}/merged_data \
  > ${DATA_DIR}/merged_data/merge_logs.log

# Stage 03: Upload to database
python scripts/03_01_upload_sample_to_db.py \
  --username admin \
  --password secret \
  --api-url http://localhost:8000 \
  --samples-dir ${DATA_DIR}/merged_data/
```

---

# Detailed Scripts Documentation

## Stage 01: Preprocessing Scripts

### 01_1_preprocess_portfolios.py

Preprocesses portfolio/researcher profile data by renaming columns using a mapping file.

**Usage:**
```bash
python scripts/01_1_preprocess_portfolios.py --portfolios-file <portfolio_csv> --output-file <output_filepath>
```

**Arguments:**
- `--portfolios-file`: Path to portfolio CSV file (also supports .parquet, .json)
- `--column-names-file`: (Optional) Path to JSON file with column mappings (default: `scripts/portfolio_column_names.json`)
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Loads column mapping from JSON file
2. Reads portfolio file (supports CSV, Parquet, JSON)
3. Renames columns according to mapping
4. Filters to keep only mapped columns
5. Converts CUIT to string type
6. Saves preprocessed data

**Output format**: Supports .csv, .parquet, .json

**Example:**
```bash
python scripts/01_1_preprocess_portfolios.py \
  --portfolios-file data/raw/portfolios.csv \
  --output-file data/preprocessed/portfolios.json
```

---

### 01_2_preprocess_enrollments.py

Preprocesses enrollment/registration data by renaming columns using a mapping file.

**Usage:**
```bash
python scripts/01_2_preprocess_enrollments.py --enrollments-file <enrollment_csv> --output-file <output_filepath>
```

**Arguments:**
- `--enrollments-file`: Path to enrollment CSV file (also supports .parquet, .json)
- `--column-names-file`: (Optional) Path to JSON file with column mappings (default: `scripts/enrollments_column_names.json`)
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Loads column mapping from JSON file
2. Reads enrollment file (supports CSV, Parquet, JSON)
3. Renames columns according to mapping (e.g., "CUIL (sin guiones)" → "cuit")
4. Filters to keep only mapped columns
5. Converts CUIT to string type
6. Saves preprocessed data

**Output format**: Supports .csv, .parquet, .json

**Example:**
```bash
python scripts/01_2_preprocess_enrollments.py \
  --enrollments-file data/raw/enrollments.csv \
  --output-file data/preprocessed/enrollments.json
```

---

### 01_3_preprocess_articles.py

Preprocesses articles/publication data by normalizing and deduplicating.

**Usage:**
```bash
python scripts/01_3_preprocess_articles.py --articles-file <articles_csv> --output-file <output_filepath>
```

**Arguments:**
- `--articles-file`: Path to articles CSV file (also supports .parquet, .json)
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Reads article file (semicolon-separated CSV)
2. Removes duplicate records based on key fields
3. Renames "cuil" column to "cuit"
4. Converts CUIT to string type
5. Saves preprocessed data

**Output format**: Supports .csv, .parquet, .json

**Example:**
```bash
python scripts/01_3_preprocess_articles.py \
  --articles-file data/raw/articles.csv \
  --output-file data/preprocessed/articles.json
```

---

### 01_4_preprocess_agreements.py

Preprocesses institutional agreements data by normalizing and deduplicating.

**Usage:**
```bash
python scripts/01_4_preprocess_agreements.py --agreements-file <agreement_csv> --output-file <output_filepath>
```

**Arguments:**
- `--agreements-file`: Path to agreement CSV file
- `--output-file`: Output filepath for preprocessed data (supports .csv, .parquet, .json)

**Processing Steps:**
1. Reads agreement file (semicolon-separated CSV)
2. Removes duplicate records
3. Renames "cuil" column to "cuit"
4. Converts CUIT to string type
5. Saves preprocessed data

**Output format**: Supports .csv, .parquet, .json

**Example:**
```bash
python scripts/01_4_preprocess_agreements.py \
  --agreements-file data/raw/agreements.csv \
  --output-file data/preprocessed/agreements.json
```

---

## Stage 02: Filtering & Merging Scripts

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
Script to upload the researcher files to the database.

The script takes a directory with files
- articles.json
- projects.json
- agreements.json
- enrollments.json

Steps, for each file:
1. Read the JSON file.
2. Parse the JSON data into the corresponding data formats (i.e. language str -> list[str], dates to ISO format)
3. Use the api endpoints to upload the data to the database in batches to avoid overloading the server.

Inputs:
    - Username and password for API authentication.
    - API base URL.
    - Path to the json files directory.


Format guidelines for the json files:
Each json file is expected to have one JSON object per line, in the following formats:

**Article Format example:**
```json
{
    "autores": "string1; string2; string3",
    "titulo": "string",
    "resumen": "string",
    "cuit": "12341234123",
    "lugar_de_trabajo": "string"
}
```

**Project Format example:**
```json
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
```

**Agreement Format example:**
```json
{
    "nombre": "ALEJANDRO MANUEL",
    "apellido": "GRANADOS",
    "cuit": 20174675962,
    "descripcion": "Determinación de proporción...",
    "tipo_produccion_tecnologica": "Servicios analíticos",
    "campo_aplicacion": "Química",
    "destinatario": null,
    "fecha_inicio": "2009-07-01 00:00:00.0",
    "fecha_fin": "2009-07-10 00:00:00.0"
}
```

**Enrollment Format example:**
```json
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
```

**Data Transformations:**
- **Articles**: `autores` (semicolon-separated) → list of strings
- **Projects**: `palabrasclaves` (semicolon-separated) → list of strings; `fecha_alta` → ISO datetime format
- **Agreements**: `cuit` → string; `fecha_inicio`/`fecha_fin` → ISO datetime format (handles milliseconds)
- **Enrollments**: `languages`, `academic_unit`, `ods` (comma-separated) → lists; `international_research_links` → boolean

Example usage:
```bash
python scripts/03_01_upload_sample_to_db.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
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

---

## Stage 05: Bulk Upload Scripts

### 05_1_upload_bulk_summaries.py

Uploads bulk summaries to the database from a JSON file containing LLM-generated researcher summaries.

**Purpose**: Upload researcher summaries that were generated by LLMs (e.g., Gemini, Ollama) to the database using the bulk summaries API endpoint.

**Input JSON Format:**

The file should be a JSON array containing summary objects. Each object must have either `researcher_id` or `researcher_cuit` (or both):

```json
[
    {
        "researcher_id": "507f1f77bcf86cd799439011",
        "model_id": "gemini-2.5-pro",
        "tag": "user_academic_temp05",
        "summary": {
            "brief": "Brief summary text",
            "profile": "Detailed profile text",
            "areas": ["area1", "area2", "area3"]
        }
    },
    {
        "researcher_cuit": "27273268885",
        "model_id": "gemini-2.5-pro",
        "tag": "user_academic_temp05",
        "summary": {
            "brief": "Another summary",
            "profile": "Another profile",
            "areas": ["area4", "area5"]
        }
    }
]
```

**Researcher Identification:**
- `researcher_id`: MongoDB ObjectId (24-character hex string)
- `researcher_cuit`: CUIT identifier (numeric string)
- If both fields are present, `researcher_id` takes precedence
- At least one identifier field must be present in each object

**Model Specification:**
- `model_id`: Model name in JSON (optional if `--model` is provided via command line)
- If both command line `--model` and JSON `model_id` are present, command line takes precedence
- All summaries must have the same `model_id` if specified in JSON
- If neither is provided, the script will exit with an error

**Usage:**
```bash
python scripts/05_1_upload_bulk_summaries.py \
    --username <api_username> \
    --password <api_password> \
    --api-url <api_base_url> \
    --summaries-file <path_to_summaries.json> \
    --tag <tag_name> \
    --model <model_name> \
    --overwrite
```

**Arguments:**
- `--username`: Username for API authentication (required)
- `--password`: Password for API authentication (required)
- `--api-url`: Base URL for the API endpoints (required, e.g., `http://localhost:8000`)
- `--summaries-file`: Path to the JSON file containing summaries (required)
- `--tag`: Tag to assign to all summaries (optional, uses tag from JSON if not provided)
- `--model`: Model name to assign to summaries (optional if `model_id` is in JSON; command line takes precedence)
- `--overwrite`: Flag to overwrite existing summaries with the same tag (optional, default: False)

**Processing Steps:**
1. Authenticates with the API to get JWT token
2. Reads summaries from JSON array file
3. Extracts `model_id` from JSON if present and validates consistency
4. Validates required fields (`researcher_id` or `researcher_cuit`, `summary`)
5. Determines model to use (command line `--model` or JSON `model_id`)
6. Builds content mapping (researcher identifier → summary JSON string)
7. Uploads all summaries in a single bulk request
8. Reports results (created, skipped, failed)

**Output:**
- Console output showing upload progress and results
- Returns counts of created, skipped, and failed summaries

**API Endpoint Used:**
- `POST /api/summaries/bulk` - Bulk upload summaries

**Tag Behavior:**
- If `--tag` is provided, it overrides any tags in the JSON file
- If `--tag` is not provided, the script uses the tag from each JSON object
- All summaries should have the same tag for consistency

**Overwrite Behavior:**
- With `--overwrite`: Replaces existing summaries with the same tag
- Without `--overwrite`: Skips researchers that already have a summary with the same tag

**Examples:**

Upload summaries with explicit tag and model:
```bash
python scripts/05_1_upload_bulk_summaries.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --summaries-file data/summaries/gemini_summaries.json \
    --tag user_academic_v1 \
    --model gemini-2.5-flash
```

Upload summaries using tag from JSON file:
```bash
python scripts/05_1_upload_bulk_summaries.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --summaries-file data/summaries/ollama_summaries.json \
    --model llama3.1
```

Upload summaries using model_id from JSON file:
```bash
python scripts/05_1_upload_bulk_summaries.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --summaries-file data/summaries/gemini_summaries_with_model.json \
    --tag user_academic_v1
```

Upload and overwrite existing summaries:
```bash
python scripts/05_1_upload_bulk_summaries.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --summaries-file data/summaries/updated_summaries.json \
    --tag user_academic_v2 \
    --model gemini-2.5-flash \
    --overwrite
```

### 05_2_upload_bulk_embeddings.py

Uploads bulk embeddings to the database from a JSON file containing researcher embedding vectors.

**Purpose**: Upload researcher embeddings (vector representations) that were generated by embedding models (e.g., Gemini, sentence transformers) to the database using the bulk embeddings API endpoint.

**Input JSON Format:**

The file should be a JSON array containing embedding objects. Each object must have either `researcher_id` or `researcher_cuit` (or both):

```json
[
    {
        "researcher_cuit": "20337008268",
        "model": "gemini-embedding-001",
        "tag": "embeddings_v1_avg",
        "embeddings": [0.0191235616, 0.0234523, -0.0153421, ...]
    },
    {
        "researcher_id": "507f1f77bcf86cd799439011",
        "model": "gemini-embedding-001",
        "tag": "embeddings_v1_avg",
        "embeddings": [0.0421532, 0.0123456, -0.0234567, ...]
    }
]
```

**Researcher Identification:**
- `researcher_id`: MongoDB ObjectId (24-character hex string)
- `researcher_cuit`: CUIT identifier (numeric string)
- If both fields are present, `researcher_id` takes precedence
- At least one identifier field must be present in each object

**Model Specification:**
- `model`: Model name in JSON (optional if `--model` is provided via command line)
- If both command line `--model` and JSON `model` are present, command line takes precedence
- All embeddings must have the same `model` if specified in JSON
- If neither is provided, the script will exit with an error

**Usage:**
```bash
python scripts/05_2_upload_bulk_embeddings.py \
    --username <api_username> \
    --password <api_password> \
    --api-url <api_base_url> \
    --embeddings-file <path_to_embeddings.json> \
    --tag <tag_name> \
    --model <model_name> \
    --overwrite
```

**Arguments:**
- `--username`: Username for API authentication (required)
- `--password`: Password for API authentication (required)
- `--api-url`: Base URL for the API endpoints (required, e.g., `http://localhost:8000`)
- `--embeddings-file`: Path to the JSON file containing embeddings (required)
- `--tag`: Tag to assign to all embeddings (optional, uses tag from JSON if not provided)
- `--model`: Model name to assign to embeddings (optional if `model` is in JSON; command line takes precedence)
- `--overwrite`: Flag to overwrite existing embeddings with the same tag (optional, default: False)

**Output:**
- Console output showing upload progress and results
- Returns counts of uploaded, skipped, and failed embeddings

**Tag Behavior:**
- If `--tag` is provided, it overrides any tags in the JSON file
- If `--tag` is not provided, the script uses the tag from each JSON object
- All embeddings should have the same tag for consistency

**Overwrite Behavior:**
- With `--overwrite`: Replaces existing embeddings with the same tag
- Without `--overwrite`: Skips researchers that already have an embedding with the same tag

**Examples:**

Upload embeddings with explicit tag and model:
```bash
python scripts/05_2_upload_bulk_embeddings.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --embeddings-file data/embeddings/gemini_embeddings.json \
    --tag embeddings_v1_avg \
    --model gemini-embedding-001
```

Upload embeddings using tag and model from JSON file:
```bash
python scripts/05_2_upload_bulk_embeddings.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --embeddings-file data/embeddings/embeddings_with_metadata.json
```

Upload and overwrite existing embeddings:
```bash
python scripts/05_2_upload_bulk_embeddings.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8000 \
    --embeddings-file data/embeddings/updated_embeddings.json \
    --tag embeddings_v2 \
    --model gemini-embedding-001 \
    --overwrite
```

### 05_3_upload_bulk_projects.py

Uploads bulk project texts from a JSON file to the database.

**Purpose**: Upload project text extracts that were extracted from project files to the database using the bulk projects API endpoint.

**Input JSON Format:**

The file should be a JSON object mapping file names to extracted text. Keys follow the format `"<cuit>_<codigo_tramite>_<filename>"`:

```json
{
    "20337008268_CB123456_plan_trabajo.pdf": "Extracted project text...",
    "27273268885_CB789012_fundamentacion.pdf": "Another project text..."
}
```

**Usage:**
```bash
python scripts/05_3_upload_bulk_projects.py \
    --input-file path/to/project_texts.json \
    --api-url http://localhost:8000 \
    --username admin \
    --password secret \
    --overwrite
```

**Arguments:**
- `--input-file`: Path to the JSON file with project texts (required)
- `--api-url`: Base URL for the API endpoints (required)
- `--username`: Username for API authentication (required)
- `--password`: Password for API authentication (required)
- `--overwrite`: Flag to overwrite existing entries (optional, default: False)

**Processing Steps:**
1. Authenticates with the API to get JWT token
2. Reads project texts from JSON file
3. Parses file names to extract cuit and codigo_tramite
4. Uploads projects in batches of 25
5. Reports results (created, skipped)

**Output:**
- Console output showing upload progress and results
- Returns counts of created and skipped project entries
