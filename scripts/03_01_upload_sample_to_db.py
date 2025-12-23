"""
Script to upload the sample .json files to the database.

Files to upload:
- articles.json
- projects.json
- enrollments.json
- agreements.json

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

Agreement Format example:
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

Example usage:
python scripts/03_01_upload_sample_to_db.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8123 \
    --samples-dir path/to/samples
"""

import json
from typing import List, Type
from pydantic import BaseModel, ValidationError
import requests
import time
import unicodedata
from datetime import datetime

from mapa_ciencia_unc.models.article import ArticleCreate
from mapa_ciencia_unc.models.project import ProjectCreate
from mapa_ciencia_unc.models.agreement import AgreementCreate
from mapa_ciencia_unc.models.researcher import ResearcherCreate


LOGIN_ENDPOINT = "/login"
BULK_ENDPOINT = "/api/{model}/bulk"


def format_validation_error(
    error: ValidationError, record_identifier: str = None
) -> str:
    """
    Format Pydantic ValidationError into human-readable message.

    Args:
        error: The Pydantic ValidationError
        record_identifier: Optional string to identify which record failed (e.g., title, CUIT)

    Returns:
        Formatted error message string
    """
    error_messages = []

    if record_identifier:
        error_messages.append(f"Validation failed for: {record_identifier}")
    else:
        error_messages.append("Validation failed")

    for err in error.errors():
        field = " -> ".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        error_type = err["type"]

        # Make error messages more user-friendly
        if error_type == "missing":
            friendly_msg = f"Missing required field: '{field}'"
        elif error_type == "string_type":
            friendly_msg = f"Field '{field}' must be text (found: {err.get('input', 'unknown type')})"
        elif error_type == "int_type":
            friendly_msg = f"Field '{field}' must be a number (found: {err.get('input', 'unknown type')})"
        elif error_type == "list_type":
            friendly_msg = f"Field '{field}' must be a list (found: {err.get('input', 'unknown type')})"
        elif error_type == "string_too_short":
            min_length = err.get("ctx", {}).get("min_length", "unknown")
            friendly_msg = (
                f"Field '{field}' is too short (minimum length: {min_length})"
            )
        elif error_type == "string_too_long":
            max_length = err.get("ctx", {}).get("max_length", "unknown")
            friendly_msg = f"Field '{field}' is too long (maximum length: {max_length})"
        elif error_type == "value_error":
            friendly_msg = f"Invalid value for '{field}': {msg}"
        else:
            # Fall back to original message for unknown error types
            friendly_msg = f"Field '{field}': {msg}"

        error_messages.append(f"  • {friendly_msg}")

    return "\n".join(error_messages)


def get_token(username, password, url):
    """
    Get an authentication token from the API.
    """
    response = requests.post(
        url,
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def normalize_language(lang):
    lang = lang.lower()
    # remove accents
    return "".join(
        c for c in unicodedata.normalize("NFD", lang) if unicodedata.category(c) != "Mn"
    )


def parse_date(date_str):
    # parse dates in project and convert to ISO format YYYY-MM-DD
    # example 2014-01-13 01:30:24
    original_format = "%Y-%m-%d %H:%M:%S"
    dt = datetime.strptime(date_str, original_format)
    # convert to datetime ISO format that mongo accepts
    # should include date and time
    return dt.isoformat()


def upload_data(data: List[BaseModel], model, batch_size, api_url, headers):
    endpoint = api_url + BULK_ENDPOINT.format(model=model)
    created = []
    failed = []
    for index in range(0, len(data), batch_size):
        batch = data[index : index + batch_size]
        batch = [m.model_dump(mode='json') for m in batch]  # Convert back model to dict
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=batch,
            )
            response_data = response.json()
        except TypeError:
            failed.extend(batch)  # Assume entire batch was bad
            continue

        created.extend(response_data.get("created", []))
        failed.extend(response_data.get("failed", []))

    print(f"Uploaded {len(created)} {model} out of {len(data)}.")
    if failed:
        print(f"Failed to upload {len(failed)} {model}")


def validate_model(
    data: dict,
    model_cls: Type[BaseModel],
    line_num: int = None,
    id_attribute: str = None,
):
    """
    Validate against model_cls model and returns readable ValidationError strings.

    Args:
        data: (dict) the object to validate
        model_cls: (class) the BaseModel class
        line_num (int): Optional. the line number of the object
        id_attribute: (str) the name of an attribute to use as identifier
            on the validation error message
    """
    data_model = None
    validation_error = None
    try:
        data_model = model_cls(**data)

    except ValidationError as e:
        # Create identifier for this article
        identifier = (
            str(data.get(id_attribute, "missing"))[:50] + "..."
            if id_attribute and data.get(id_attribute)
            else f"Line {line_num}"
        )

        # Format the error nicely
        error_msg = format_validation_error(e, identifier)
        validation_error = {
            "line": line_num,
            "identifier": identifier,
            "error": error_msg,
        }

    except Exception as e:
        # Catch any other unexpected errors
        identifier = f"Line {line_num}"
        validation_error = {
            "line": line_num,
            "identifier": identifier,
            "error": f"Unexpected error: {str(e)}",
        }

    return data_model, validation_error


def print_validation_summary(
    validated_objets: list, validation_errors: List[str], object_name: str
):
    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"✓ Valid {object_name}: {len(validated_objets)}")
    print(f"✗ Invalid {object_name}: {len(validation_errors)}")

    if validation_errors:
        print(f"\n{'=' * 60}")
        print("SHOWING FIRST 5 VALIDATION ERRORS")
        print(f"{'=' * 60}")
        for err in validation_errors[:5]:  # Show first 5 errors
            print(f"\n{err['error']}")

        if len(validation_errors) > 5:
            print(f"\n... and {len(validation_errors) - 5} more errors")

        print(f"\n{'=' * 60}")
        print("WARNING: Some articles failed validation and will be skipped")
        print(f"{'=' * 60}\n")


def upload_articles(samples_dir):
    """
    Parses and validates articles from JSON file.

    Returns:
        Tuple of (valid_articles, validation_errors)
    """
    articles_path = f"{samples_dir}/articles.json"
    raw_articles = []

    print(f"Reading articles from: {articles_path}")
    with open(articles_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                article = json.loads(line)
                article["cuit"] = str(article.get("cuit"))
                raw_articles.append((line_num, article))
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_num} contains invalid JSON: {e}")

    print(f"  - Found {len(raw_articles)} articles to process\n")

    validated_articles = []
    validation_errors = []

    print("Validating articles against database schema...")
    for line_num, article in raw_articles:
        validated_article, validation_error = validate_model(
            article, model_cls=ArticleCreate, line_num=line_num, id_attribute="cuit"
        )
        if validated_article:
            validated_articles.append(validated_article)
        elif validation_error:
            validation_errors.append(validation_error)
        else:
            print(f"Error! Validation for line {line_num} failed.")

    return validated_articles, validation_errors


def upload_enrollments(samples_dir):
    """
    Parses and validates enrollments from JSON file.

    Returns:
        Tuple of (valid_enrollments, validation_errors)
    """
    enrollments_path = f"{samples_dir}/enrollment.json"
    raw_enrollments = []

    print(f"Reading enrollments from: {enrollments_path}")
    with open(enrollments_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                enrollment = json.loads(line)
                raw_enrollments.append((line_num, enrollment))
            except json.JSONDecodeError as e:
                print(f"  ⚠ Warning: Line {line_num} contains invalid JSON: {e}")

    print(f"  - Found {len(raw_enrollments)} enrollments to process\n")

    validated_enrollments = []
    validation_errors = []

    print("Validating enrollments against database schema...")
    for line_num, e in raw_enrollments:
        try:
            # Preprocess enrollment data
            # ensure cuit is str
            e["cuit"] = str(e["cuit"])

            # languages to list of str
            langs = e.get("languages")
            if isinstance(langs, str):
                e["languages"] = [
                    normalize_language(l.strip()) for l in langs.split(",") if l.strip()
                ]
            elif langs is None:
                e["languages"] = []

            # academic_units to list of str, rename from academic_unit
            au = e.get("academic_unit")
            if isinstance(au, str):
                e["academic_units"] = [x.strip() for x in au.split(",") if x.strip()]
            elif au is not None:
                e["academic_units"] = au
            else:
                e["academic_units"] = []
            # remove old key
            e.pop("academic_unit", None)

            # ods to list of str
            ods = e.get("ods")
            if isinstance(ods, str):
                e["ods"] = [x.strip() for x in ods.split(",") if x.strip()]
            elif ods is None or ods == ["No se encuentra alineado con ningún ODS"]:
                e["ods"] = []

            # international_research_links to bool
            irl = e.get("international_research_links", "No")
            e["international_research_links"] = irl != "No"

            # orcid_number: if it's a url, extract the number after the last /
            orcid = e.get("orcid_number")
            if isinstance(orcid, str) and orcid.startswith("http"):
                e["orcid_number"] = orcid.split("/")[-1]

            # Validate against ResearcherCreate model
            validated_enrollment, validation_error = validate_model(
                e, model_cls=ResearcherCreate, line_num=line_num, id_attribute="cuit"
            )
            if validated_enrollment:
                validated_enrollments.append(validated_enrollment)
            elif validation_error:
                validation_errors.append(validation_error)
            else:
                print(f"Error! Validation for line {line_num} failed.")

        except Exception as ex:
            # Catch preprocessing errors
            identifier = f"Line {line_num} (CUIT: {e.get('cuit', 'missing')})"
            validation_errors.append(
                {
                    "line": line_num,
                    "identifier": identifier,
                    "error": f"Preprocessing error: {str(ex)}",
                }
            )

    return validated_enrollments, validation_errors


def upload_projects(samples_dir):
    """
    Parses and validates projects from JSON file.

    Returns:
        Tuple of (valid_projects, validation_errors)
    """
    projects_path = f"{samples_dir}/projects.json"
    raw_projects = []

    print(f"Reading projects from: {projects_path}")
    with open(projects_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                project = json.loads(line)
                raw_projects.append((line_num, project))
            except json.JSONDecodeError as e:
                print(f"  ⚠ Warning: Line {line_num} contains invalid JSON: {e}")

    print(f"  - Found {len(raw_projects)} projects to process\n")

    validated_projects = []
    validation_errors = []

    print("Validating projects against database schema...")
    for line_num, project in raw_projects:
        try:
            # Preprocess project data
            # cuit to str
            project["cuit"] = str(project["cuit"])

            # palabrasclave to list split by ;
            palabrasclaves = project.get("palabrasclaves", "")
            if isinstance(palabrasclaves, str):
                project["palabrasclaves"] = [
                    pk.strip() for pk in palabrasclaves.split(";") if pk.strip()
                ]

            # convocatoria id to str
            project["convocatoria_id"] = str(project["convocatoria_id"])

            # fecha_alta to ISO format
            date_key = "fecha_alta"
            date_str = project.get(date_key)
            if isinstance(date_str, str) and date_str.strip() != "":
                project[date_key] = parse_date(date_str)

            # Validate against ProjectCreate model
            validated_project, validation_error = validate_model(
                project,
                model_cls=ProjectCreate,
                line_num=line_num,
                id_attribute="codigo_tramite",
            )
            if validated_project:
                validated_projects.append(validated_project)
            elif validation_error:
                validation_errors.append(validation_error)
            else:
                print(f"Error! Validation for line {line_num} failed.")

        except Exception as ex:
            # Catch preprocessing errors
            identifier = (
                f"Line {line_num} (CUIT: {project.get('cuit', 'missing')}, "
                f"codigo_tramite: {project.get('codigo_tramite', 'missing')})"
            )
            validation_errors.append(
                {
                    "line": line_num,
                    "identifier": identifier,
                    "error": f"Preprocessing error: {str(ex)}",
                }
            )

    return validated_projects, validation_errors


def upload_agreements(samples_dir):
    """
    Parses and validates agreements from JSON file.

    Returns:
        Tuple of (valid_agreements, validation_errors)
    """
    agreements_path = f"{samples_dir}/agreements.json"
    raw_agreements = []

    print(f"Reading agreements from: {agreements_path}")
    with open(agreements_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                agreement = json.loads(line)
                raw_agreements.append((line_num, agreement))
            except json.JSONDecodeError as e:
                print(f"  ⚠ Warning: Line {line_num} contains invalid JSON: {e}")

    print(f"  - Found {len(raw_agreements)} agreements to process\n")

    validated_agreements = []
    validation_errors = []

    print("Validating agreements against database schema...")
    for line_num, agreement in raw_agreements:
        try:
            # Preprocess agreement data
            # cuit to str
            agreement["cuit"] = str(agreement["cuit"])

            # fecha_inicio to ISO format if present
            if "fecha_inicio" in agreement and agreement["fecha_inicio"]:
                date_str = agreement["fecha_inicio"]
                if isinstance(date_str, str) and date_str.strip():
                    # Handle format with milliseconds: "2009-07-01 00:00:00.0"
                    if "." in date_str:
                        date_str = date_str.split(".")[0]
                    agreement["fecha_inicio"] = parse_date(date_str)
                else:
                    agreement["fecha_inicio"] = None

            # fecha_fin to ISO format if present
            if "fecha_fin" in agreement and agreement["fecha_fin"]:
                date_str = agreement["fecha_fin"]
                if isinstance(date_str, str) and date_str.strip():
                    # Handle format with milliseconds: "2009-07-10 00:00:00.0"
                    if "." in date_str:
                        date_str = date_str.split(".")[0]
                    agreement["fecha_fin"] = parse_date(date_str)
                else:
                    agreement["fecha_fin"] = None

            # Validate against AgreementCreate model
            validated_agreement, validation_error = validate_model(
                agreement,
                model_cls=AgreementCreate,
                line_num=line_num,
                id_attribute="cuit",
            )
            if validated_agreement:
                validated_agreements.append(validated_agreement)
            elif validation_error:
                validation_errors.append(validation_error)
            else:
                print(f"Error! Validation for line {line_num} failed.")

        except Exception as ex:
            # Catch preprocessing errors
            identifier = f"Line {line_num} (CUIT: {agreement.get('cuit', 'missing')})"
            validation_errors.append(
                {
                    "line": line_num,
                    "identifier": identifier,
                    "error": f"Preprocessing error: {str(ex)}",
                }
            )

    return validated_agreements, validation_errors


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload sample data to the database via API."
    )
    parser.add_argument(
        "--username", type=str, required=True, help="Username for API authentication"
    )
    parser.add_argument(
        "--password", type=str, required=True, help="Password for API authentication"
    )
    parser.add_argument(
        "--api-url", type=str, required=True, help="Base URL for the API endpoints"
    )
    # path to sample files dir
    parser.add_argument(
        "--samples-dir",
        type=str,
        help="Path to the sample files directory",
    )

    return parser.parse_args()


def parse_and_upload(username, password, api_url, samples_dir, batch_size):
    start_time = time.time()
    token = get_token(username, password, url=api_url + LOGIN_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}

    samples_dir = samples_dir.rstrip("/")

    # parse and upload enrollments
    print("\n" + "=" * 60)
    print("UPLOADING ENROLLMENTS (RESEARCHERS)")
    print("=" * 60)
    enrollments, validation_errors = upload_enrollments(samples_dir)
    print_validation_summary(enrollments, validation_errors, "enrollments")

    if not enrollments:
        print(
            "\n❌ No valid enrollments to upload. Please fix validation errors and try again."
        )
        return

    print(f"\nUploading {len(enrollments)} valid enrollments to database...")
    upload_data(
        enrollments,
        model="researchers",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    # parse and upload articles
    print("\n" + "=" * 60)
    print("UPLOADING ARTICLES")
    print("=" * 60)
    articles, validation_errors = upload_articles(samples_dir)
    print_validation_summary(articles, validation_errors, "articles")

    if not articles:
        print(
            "\n❌ No valid articles to upload. Please fix validation errors and try again."
        )
        return

    print(f"\nUploading {len(articles)} valid articles to database...")
    upload_data(
        articles,
        model="articles",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    # parse and upload projects
    print("\n" + "=" * 60)
    print("UPLOADING PROJECTS")
    print("=" * 60)
    projects, validation_errors = upload_projects(samples_dir)
    print_validation_summary(projects, validation_errors, "projects")

    if not projects:
        print(
            "\n❌ No valid projects to upload. Please fix validation errors and try again."
        )
        return

    print(f"\nUploading {len(projects)} valid projects to database...")
    upload_data(
        projects,
        model="projects",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    # parse and upload agreements
    print("\n" + "=" * 60)
    print("UPLOADING AGREEMENTS")
    print("=" * 60)
    agreements, validation_errors = upload_agreements(samples_dir)
    print_validation_summary(agreements, validation_errors, "agreements")

    if not agreements:
        print(
            "\n❌ No valid agreements to upload. Please fix validation errors and try again."
        )
        return

    print(f"\nUploading {len(agreements)} valid agreements to database...")
    upload_data(
        agreements,
        model="agreements",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    end_time = time.time()
    print("\n" + "=" * 60)
    print(f"UPLOAD COMPLETE - Total time: {end_time - start_time:.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    parse_and_upload(
        username=args.username,
        password=args.password,
        api_url=args.api_url,
        samples_dir=args.samples_dir,
        batch_size=100,
    )
