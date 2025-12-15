"""
This process uploads projects texts from a json file to the database.

Inputs:
    - A json file with project texts. The json keys are expected to be "<cuit>_<codigo_tramite>_<filename>"
    - The API url to upload the data to.
    - Username and password for API authentication.
    - Overwrite flag to indicate whether to overwrite existing entries in the database. (based on cuit and codigo_tramite)

Example usage:
python processes/upload_projects_to_db.py \
    --input-file path/to/project_texts.json \
    --api-url http://localhost:8123 \
    --username admin \
    --password secret \
    --overwrite
"""

import json
import requests
import time
import argparse

LOGIN_ENDPOINT = "/login"
BULK_ENDPOINT = "/api/projects/extracted_intros/bulk"


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


def upload_data(data, batch_size, api_url, headers):
    endpoint = api_url + BULK_ENDPOINT
    created = 0
    skipped = 0
    for index in range(0, len(data), batch_size):
        batch = data[index : index + batch_size]
        response = requests.post(
            endpoint,
            headers=headers,
            json=batch,
        )
        response_data = response.json()
        created += response_data.get("created", 0)
        skipped += response_data.get("skipped", 0)

    print(f"Uploaded {created} entries out of {len(data)}.")
    print(f"Skipped entries: {skipped}")


def parse_file_name(file_name):
    """
    Parse the file name to extract cuit and codigo_tramite.
    Expected format: "<cuit>_<codigo_tramite>_<filename>"
    """
    parts = file_name.split("_")
    if len(parts) < 3:
        raise ValueError(f"Invalid file name format: {file_name}")
    cuit = parts[0]
    codigo_tramite = parts[1]
    return cuit, codigo_tramite


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload project texts to the database via API."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        required=True,
        help="Path to the input JSON file with project texts.",
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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing entries in the database.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_time = time.time()
    token = get_token(args.username, args.password, url=args.api_url + LOGIN_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}
    batch_size = 25
    with open(args.input_file, "r", encoding="utf-8") as f:
        project_texts = json.load(f)

    payload = []
    for file_name, text in project_texts.items():
        cuit, codigo_tramite = parse_file_name(file_name)
        payload.append(
            {
                "cuit": cuit,
                "codigo_tramite": codigo_tramite,
                "extracted_intro": text,
            }
        )
    upload_data(payload, batch_size, args.api_url, headers)
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")
