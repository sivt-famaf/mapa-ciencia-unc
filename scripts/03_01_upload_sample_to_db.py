"""
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
python scripts/03_01_upload_sample_to_db.py \
    --username admin \
    --password secret \
    --api-url http://localhost:8123 \
    --samples-dir path/to/samples
"""

import json
import requests
import time
import unicodedata
from datetime import datetime


LOGIN_ENDPOINT = "/login"
BULK_ENDPOINT = "/api/{model}/bulk"


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


def parse_articles(samples_dir):
    articles_path = f"{samples_dir}/articles.json"
    articles = []
    with open(articles_path, "r") as f:
        for line in f:
            article = json.loads(line)
            articles.append(article)

    for article in articles:
        # split authors by ;
        if "autores" in article:
            autores = article["autores"]
            if isinstance(autores, str):
                article["autores"] = [
                    a.strip() for a in autores.split(";") if a.strip()
                ]

    return articles


def parse_enrollments(samples_dir):
    enrollments_path = f"{samples_dir}/enrollment.json"
    enrollments = []
    with open(enrollments_path, "r") as f:
        for line in f:
            enrollments.append(json.loads(line))

    for e in enrollments:
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

    return enrollments


def parse_projects(samples_dir):
    projects_path = f"{samples_dir}/projects.json"
    projects = []
    with open(projects_path, "r") as f:
        for line in f:
            project = json.loads(line)
            projects.append(project)

    for project in projects:
        # cuit to str
        project["cuit"] = str(project["cuit"])

        # palabrasclave to list split by ;
        palabrasclaves = project["palabrasclaves"]
        if isinstance(palabrasclaves, str):
            project["palabrasclaves"] = [
                pk.strip() for pk in palabrasclaves.split(";") if pk.strip()
            ]

        # convocatoria id to str
        project["convocatoria_id"] = str(project["convocatoria_id"])

        # fecha_alta to ISO format
        date_key = "fecha_alta"
        date_str = project[date_key]
        if isinstance(date_str, str) and date_str.strip() != "":
            project[date_key] = parse_date(date_str)

    return projects


def upload_data(data, model, batch_size, api_url, headers):
    endpoint = api_url + BULK_ENDPOINT.format(model=model)
    created = []
    failed = []
    for index in range(0, len(data), batch_size):
        batch = data[index : index + batch_size]
        response = requests.post(
            endpoint,
            headers=headers,
            json=batch,
        )
        response_data = response.json()
        created.extend(response_data.get("created", []))
        failed.extend(response_data.get("failed", []))

    print(f"Uploaded {len(created)} {model} out of {len(data)}.")
    if failed:
        print(f"Failed {model}:")
        for f in failed:
            print(f)


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
    batch_size = 100

    # parse and upload articles
    articles = parse_articles(samples_dir)
    upload_data(
        articles,
        model="articles",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    # parse and upload projects
    projects = parse_projects(samples_dir)
    upload_data(
        projects,
        model="projects",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )

    # parse and upload enrollments
    enrollments = parse_enrollments(samples_dir)
    upload_data(
        enrollments,
        model="researchers",
        batch_size=batch_size,
        api_url=api_url,
        headers=headers,
    )
    end_time = time.time()
    print(f"Total upload time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    args = parse_args()
    parse_and_upload(
        username=args.username,
        password=args.password,
        api_url=args.api_url,
        samples_dir=args.samples_dir,
        batch_size=100,
    )
