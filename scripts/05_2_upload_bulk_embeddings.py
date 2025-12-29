"""
Script to upload bulk embeddings to the database from a JSON file.

This script reads a JSON file containing researcher embeddings and uploads them
to the database using the bulk embeddings endpoint. The JSON file should be an
array of embedding objects.

Input JSON Format:
    The file should be a JSON array containing embedding objects.
    Each object must have either 'researcher_id' or 'researcher_cuit' (or both):
    [
        {
            "researcher_cuit": "20337008268",
            "model": "gemini-embedding-001",
            "tag": "embeddings_v1_avg",
            "embeddings": [0.0191235616, 0.0234523, ...]
        },
        {
            "researcher_id": "507f1f77bcf86cd799439011",
            "model": "gemini-embedding-001",
            "tag": "embeddings_v1_avg",
            "embeddings": [0.0421532, 0.0123456, ...]
        }
    ]

    Notes:
    - researcher_id should be a MongoDB ObjectId (24-character hex string)
    - researcher_cuit should be a CUIT identifier (numeric string)
    - If both fields are present, researcher_id takes precedence
    - At least one identifier field must be present
    - model is optional in JSON if --model is provided via command line
    - All embeddings must have the same model if specified in JSON
    - All embeddings must have the same tag if --tag is not provided
    - The 'embeddings' field contains the vector data

Process:
    1. Read the JSON array from file
    2. Parse each embedding object
    3. Build a vector_mapping dictionary (researcher_id -> embedding vector)
    4. Upload all embeddings in a single bulk request to the API

Arguments:
    --username: Username for API authentication
    --password: Password for API authentication
    --api-url: Base URL for the API (e.g., http://localhost:8123)
    --embeddings-file: Path to the JSON file containing embeddings
    --tag: Tag to assign to all embeddings (optional, will use tag from file if not provided)
    --model: Model name to assign to all embeddings (optional, defaults
        to model in the first embedding or "unknown")
    --overwrite: Whether to overwrite existing embeddings with the same tag (flag, default: False)

Example usage:
    python scripts/05_2_upload_bulk_embeddings.py \
        --username admin \
        --password secret \
        --api-url http://localhost:8123 \
        --embeddings-file path/to/embeddings.json \
        --tag embeddings_v1_avg \
        --model gemini-embedding-001 \
        --overwrite

Notes:
    - If --tag is not provided, the script will use the tag from each JSON object
    - All embeddings in the file should have the same tag if --tag is not specified
    - The embeddings field will be used as the vector data
    - The API endpoint is: /api/embeddings/upload_bulk
"""

import json
import argparse
import requests
import time
from typing import Dict, Tuple, Optional, List


LOGIN_ENDPOINT = "/login"
BULK_EMBEDDINGS_ENDPOINT = "/api/embeddings/upload/bulk"


def get_token(username: str, password: str, url: str) -> str:
    """
    Get an authentication token from the API.

    Args:
        username: API username
        password: API password
        url: Full URL to the login endpoint

    Returns:
        JWT access token string

    Raises:
        requests.HTTPError: If authentication fails
    """
    response = requests.post(
        url,
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def read_embeddings_file(file_path: str) -> Tuple[Dict[str, dict], Optional[str]]:
    """
    Read embeddings from a JSON array file.

    The file should contain a JSON array of objects, each with:
    - researcher_id OR researcher_cuit: str (at least one required)
    - tag: str
    - embeddings: list[float] (the embedding vector)
    - model: str (optional, if not provided via --model argument)

    If both researcher_id and researcher_cuit are present, researcher_id takes precedence.

    Args:
        file_path: Path to the JSON file

    Returns:
        Tuple of:
        - Dictionary mapping researcher identifier -> full embedding object
        - Model ID extracted from JSON (or None if not present/inconsistent)

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        ValueError: If model IDs are inconsistent across objects
    """
    embeddings = {}
    extracted_model_id = None
    model_ids_seen = set()

    print(f"Reading embeddings from: {file_path}")
    with open(file_path, "r") as f:
        try:
            # Load entire JSON array
            data = json.load(f)

            # Validate it's a list
            if not isinstance(data, list):
                raise ValueError("JSON file must contain an array of embedding objects")

            # Process each embedding object
            for idx, obj in enumerate(data):
                # Extract researcher identifier (prefer researcher_id over researcher_cuit)
                researcher_identifier = None
                if "researcher_id" in obj and obj["researcher_id"]:
                    researcher_identifier = str(obj["researcher_id"])
                elif "researcher_cuit" in obj and obj["researcher_cuit"]:
                    researcher_identifier = str(obj["researcher_cuit"])

                if not researcher_identifier:
                    print(
                        f"     Warning: Item {idx} missing both researcher_id and researcher_cuit, skipping"
                    )
                    continue

                if "embeddings" not in obj:
                    print(
                        f"     Warning: Item {idx} missing embeddings field, skipping"
                    )
                    continue

                # Validate embeddings is a list of numbers
                if not isinstance(obj["embeddings"], list) or not obj["embeddings"]:
                    print(
                        f"     Warning: Item {idx} has invalid embeddings field, skipping"
                    )
                    continue

                # Track model if present
                if "model" in obj and obj["model"]:
                    model_ids_seen.add(obj["model"])

                embeddings[researcher_identifier] = obj

        except json.JSONDecodeError as e:
            print(f"     Error: Invalid JSON in file: {e}")
            raise

    # Validate model consistency
    if len(model_ids_seen) > 1:
        raise ValueError(
            f"Inconsistent model IDs found in JSON: {model_ids_seen}. "
            "All embeddings must use the same model."
        )
    elif len(model_ids_seen) == 1:
        extracted_model_id = model_ids_seen.pop()
        print(f"  - Extracted model from JSON: {extracted_model_id}")

    print(f"  - Successfully read {len(embeddings)} embeddings\n")
    return embeddings, extracted_model_id


def build_vector_mapping(embeddings: Dict[str, dict]) -> Dict[str, List[float]]:
    """
    Build vector_mapping from embeddings dictionary.

    Extracts the embeddings vector for each researcher.

    Args:
        embeddings: Dictionary of researcher identifier -> embedding object

    Returns:
        Dictionary of researcher identifier -> embedding vector
    """
    vector_mapping = {}

    for identifier, obj in embeddings.items():
        # Extract embedding vector
        vector = obj["embeddings"]
        vector_mapping[identifier] = vector

    return vector_mapping


def upload_embeddings(
    vector_mapping: Dict[str, List[float]],
    tag: str,
    model: str,
    overwrite: bool,
    api_url: str,
    headers: dict,
) -> dict:
    """
    Upload embeddings to the database via bulk endpoint.

    Args:
        vector_mapping: Dictionary mapping researcher identifier (ID or CUIT) -> embedding vector
        tag: Tag to assign to embeddings
        model: Model name to assign to embeddings
        overwrite: Whether to overwrite existing embeddings
        api_url: Base API URL
        headers: Request headers (including auth token)

    Returns:
        Response JSON from the API

    Raises:
        requests.HTTPError: If upload fails
    """
    endpoint = api_url + BULK_EMBEDDINGS_ENDPOINT

    payload = {
        "overwrite": overwrite,
        "model": model,
        "tag": tag,
        "vector_mapping": vector_mapping,
    }

    print(f"Uploading {len(vector_mapping)} embeddings to database...")
    print(f"  - Tag: {tag}")
    print(f"  - Model: {model}")
    print(f"  - Overwrite: {overwrite}\n")

    response = requests.post(
        endpoint,
        headers=headers,
        json=payload,
    )
    response.raise_for_status()

    return response.json()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload bulk embeddings to the database from a JSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python scripts/05_2_upload_bulk_embeddings.py \\
      --username admin \\
      --password secret \\
      --api-url http://localhost:8123 \\
      --embeddings-file data/embeddings.json \\
      --tag embeddings_v1_avg \\
      --model gemini-embedding-001 \\
      --overwrite
        """,
    )

    parser.add_argument(
        "--username", type=str, required=True, help="Username for API authentication"
    )
    parser.add_argument(
        "--password", type=str, required=True, help="Password for API authentication"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        required=True,
        help="Base URL for the API endpoints (e.g., http://localhost:8123)",
    )
    parser.add_argument(
        "--embeddings-file",
        type=str,
        required=True,
        help="Path to the JSON file containing embeddings",
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="Tag to assign to all embeddings (optional, will use tag from file if not provided)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name to assign to embeddings (optional if model present in JSON)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing embeddings with the same tag (default: False)",
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()
    start_time = time.time()

    print("\n" + "=" * 60)
    print("BULK EMBEDDING UPLOAD")
    print("=" * 60 + "\n")

    # Authenticate
    print("Authenticating...")
    try:
        token = get_token(args.username, args.password, args.api_url + LOGIN_ENDPOINT)
        headers = {"Authorization": f"Bearer {token}"}
        print("  Authentication successful\n")
    except requests.HTTPError as e:
        print(f"    Authentication failed: {e}")
        return

    # Read embeddings file
    try:
        embeddings, json_model_id = read_embeddings_file(args.embeddings_file)
    except FileNotFoundError:
        print(f"    File not found: {args.embeddings_file}")
        return
    except Exception as e:
        print(f"    Error reading file: {e}")
        return

    if not embeddings:
        print("     No valid embeddings found in file")
        return

    # Determine tag to use
    if args.tag:
        tag = args.tag
        print(f"Using tag from command line: {tag}\n")
    else:
        # Use tag from first embedding
        first_embedding = next(iter(embeddings.values()))
        tag = first_embedding.get("tag")
        if not tag:
            print("     No --tag provided and no tag found in JSON objects")
            return
        print(f"Using tag from JSON file: {tag}\n")

    # Determine model to use (command line takes precedence)
    if args.model:
        model = args.model
        print(f"Using model from command line: {model}\n")
    elif json_model_id:
        model = json_model_id
        print(f"Using model from JSON file: {model}\n")
    else:
        print(
            "     Error: No model specified. Provide --model argument or include model in JSON"
        )
        return

    # Build vector mapping
    vector_mapping = build_vector_mapping(embeddings)

    # Upload embeddings
    try:
        result = upload_embeddings(
            vector_mapping=vector_mapping,
            tag=tag,
            model=model,
            overwrite=args.overwrite,
            api_url=args.api_url,
            headers=headers,
        )

        # Print results
        print("=" * 60)
        print("UPLOAD RESULTS")
        print("=" * 60)
        print(f"  Uploaded embeddings: {result['uploaded_embeddings']}")

        if result.get("skipped_embeddings"):
            print(f"   Skipped embeddings: {len(result['skipped_embeddings'])}")
            if len(result["skipped_embeddings"]) <= 5:
                for researcher_id, reason in result["skipped_embeddings"].items():
                    print(f"    - Researcher {researcher_id}: {reason}")
            else:
                print(f"    (showing first 5)")
                for i, (researcher_id, reason) in enumerate(
                    result["skipped_embeddings"].items()
                ):
                    if i >= 5:
                        break
                    print(f"    - Researcher {researcher_id}: {reason}")

        if result.get("failed_embeddings"):
            print(f"    Failed embeddings: {len(result['failed_embeddings'])}")
            if len(result["failed_embeddings"]) <= 5:
                for researcher_id in result["failed_embeddings"]:
                    print(f"    - Researcher {researcher_id}")
            else:
                print(f"    (showing first 5)")
                for researcher_id in result["failed_embeddings"][:5]:
                    print(f"    - Researcher {researcher_id}")

        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"UPLOAD COMPLETE - Total time: {elapsed_time:.2f} seconds")
        print("=" * 60 + "\n")

    except requests.HTTPError as e:
        print(f"\n      Upload failed: {e}")
        if e.response is not None:
            print(f"  Response: {e.response.text}")
        return
    except Exception as e:
        print(f"\n      Unexpected error: {e}")
        return


if __name__ == "__main__":
    main()
