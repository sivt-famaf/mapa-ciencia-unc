# Scripts Directory

This directory contains data processing and analysis scripts for the UNC Science Map project.

Files follow the established naming convention: `NN_X_descriptive_name.py`
   - `NN`: Sequential number of the preprocessing stage
   - `X`: Sub-step number (if needed)
   - `descriptive_name`: Description of what the script does

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

