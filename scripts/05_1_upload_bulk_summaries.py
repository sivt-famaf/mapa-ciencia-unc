"""
Script to upload bulk summaries to the database from a JSON file.

This script reads a JSON file containing researcher summaries and uploads them
to the database using the bulk summaries endpoint. The JSON file should be an
array of summary objects.

Input JSON Format:
    The file should be a JSON array containing summary objects.
    Each object must have either 'researcher_id' or 'researcher_cuit' (or both):
    [
        {
            "researcher_id": "507f1f77bcf86cd799439011",
            "tag": "user_academic_temp05",
            "summary": {
                "brief": "Brief summary text",
                "profile": "Detailed profile text",
                "areas": ["area1", "area2", "area3"]
            }
        },
        {
            "researcher_cuit": "27273268885",
            "tag": "user_academic_temp05",
            "summary": {
                "brief": "Another summary",
                "profile": "Another profile",
                "areas": ["area4", "area5"]
            }
        }
    ]

    Notes:
    - researcher_id should be a MongoDB ObjectId (24-character hex string)
    - researcher_cuit should be a CUIT identifier (numeric string)
    - If both fields are present, researcher_id takes precedence
    - At least one identifier field must be present

Process:
    1. Read the JSON array from file
    2. Parse each summary object
    3. Build a content_mapping dictionary (researcher_id -> summary JSON string)
    4. Upload all summaries in a single bulk request to the API

Arguments:
    --username: Username for API authentication
    --password: Password for API authentication
    --api-url: Base URL for the API (e.g., http://localhost:8123)
    --summaries-file: Path to the JSON file containing summaries
    --tag: Tag to assign to all summaries (optional, will use tag from file if not provided)
    --model: Model name to assign to all summaries (optional, defaults to "unknown")
    --overwrite: Whether to overwrite existing summaries with the same tag (flag, default: False)

Example usage:
    python scripts/05_1_upload_bulk_summaries.py \
        --username admin \
        --password secret \
        --api-url http://localhost:8123 \
        --summaries-file path/to/summaries.json \
        --tag user_academic_v1 \
        --model gemini-2.5-flash \
        --overwrite

Notes:
    - If --tag is not provided, the script will use the tag from each JSON object
    - All summaries in the file should have the same tag if --tag is not specified
    - The summary field will be converted to a JSON string before uploading
    - The API endpoint is: /api/summaries/bulk
"""

import json
import argparse
import requests
import time
from typing import Dict


LOGIN_ENDPOINT = "/login"
BULK_SUMMARIES_ENDPOINT = "/api/summaries/bulk"


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


def read_summaries_file(file_path: str) -> Dict[str, dict]:
    """
    Read summaries from a JSON array file.

    The file should contain a JSON array of objects, each with:
    - researcher_id OR researcher_cuit: str (at least one required)
    - tag: str
    - summary: dict (will be converted to JSON string)

    If both researcher_id and researcher_cuit are present, researcher_id takes precedence.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary mapping researcher identifier -> full summary object

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    summaries = {}

    print(f"Reading summaries from: {file_path}")
    with open(file_path, "r") as f:
        try:
            # Load entire JSON array
            data = json.load(f)

            # Validate it's a list
            if not isinstance(data, list):
                raise ValueError("JSON file must contain an array of summary objects")

            # Process each summary object
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

                if "summary" not in obj:
                    print(f"     Warning: Item {idx} missing summary field, skipping")
                    continue

                summaries[researcher_identifier] = obj

        except json.JSONDecodeError as e:
            print(f"     Error: Invalid JSON in file: {e}")
            raise

    print(f"  - Successfully read {len(summaries)} summaries\n")
    return summaries


def build_content_mapping(summaries: Dict[str, dict]) -> Dict[str, str]:
    """
    Build content_mapping from summaries dictionary.

    Converts the summary dict to a JSON string for each researcher.

    Args:
        summaries: Dictionary of researcher identifier -> summary object

    Returns:
        Dictionary of researcher identifier -> summary JSON string
    """
    content_mapping = {}

    for identifier, obj in summaries.items():
        # Convert summary dict to JSON string
        summary_content = json.dumps(obj["summary"])
        content_mapping[identifier] = summary_content

    return content_mapping


def upload_summaries(
    content_mapping: Dict[str, str],
    tag: str,
    model: str,
    overwrite: bool,
    api_url: str,
    headers: dict,
) -> dict:
    """
    Upload summaries to the database via bulk endpoint.

    Args:
        content_mapping: Dictionary mapping researcher identifier (ID or CUIT) -> summary JSON string
        tag: Tag to assign to summaries
        model: Model name to assign to summaries
        overwrite: Whether to overwrite existing summaries
        api_url: Base API URL
        headers: Request headers (including auth token)

    Returns:
        Response JSON from the API

    Raises:
        requests.HTTPError: If upload fails
    """
    endpoint = api_url + BULK_SUMMARIES_ENDPOINT

    payload = {
        "overwrite": overwrite,
        "model": model,
        "tag": tag,
        "content_mapping": content_mapping,
    }

    print(f"Uploading {len(content_mapping)} summaries to database...")
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
        description="Upload bulk summaries to the database from a JSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python scripts/05_1_upload_bulk_summaries.py \\
      --username admin \\
      --password secret \\
      --api-url http://localhost:8123 \\
      --summaries-file data/summaries.json \\
      --tag user_academic_v1 \\
      --model gemini-2.5-flash \\
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
        "--summaries-file",
        type=str,
        required=True,
        help="Path to the JSON file containing summaries",
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="Tag to assign to all summaries (optional, will use tag from file if not provided)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="unknown",
        help="Model name to assign to summaries (default: unknown)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing summaries with the same tag (default: False)",
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()
    start_time = time.time()

    print("\n" + "=" * 60)
    print("BULK SUMMARY UPLOAD")
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

    # Read summaries file
    try:
        summaries = read_summaries_file(args.summaries_file)
    except FileNotFoundError:
        print(f"    File not found: {args.summaries_file}")
        return
    except Exception as e:
        print(f"    Error reading file: {e}")
        return

    if not summaries:
        print("     No valid summaries found in file")
        return

    # Determine tag to use
    if args.tag:
        tag = args.tag
        print(f"Using tag from command line: {tag}\n")
    else:
        # Use tag from first summary
        first_summary = next(iter(summaries.values()))
        tag = first_summary.get("tag")
        if not tag:
            print("     No --tag provided and no tag found in JSON objects")
            return
        print(f"Using tag from JSON file: {tag}\n")

    # Build content mapping
    content_mapping = build_content_mapping(summaries)

    # Upload summaries
    try:
        result = upload_summaries(
            content_mapping=content_mapping,
            tag=tag,
            model=args.model,
            overwrite=args.overwrite,
            api_url=args.api_url,
            headers=headers,
        )

        # Print results
        print("=" * 60)
        print("UPLOAD RESULTS")
        print("=" * 60)
        print(f"  Created summaries: {result['created_summaries']}")

        if result.get("skipped_summaries"):
            print(f"  � Skipped summaries: {len(result['skipped_summaries'])}")
            if len(result["skipped_summaries"]) <= 5:
                for researcher_id, reason in result["skipped_summaries"].items():
                    print(f"    - Researcher {researcher_id}: {reason}")
            else:
                print(f"    (showing first 5)")
                for i, (researcher_id, reason) in enumerate(
                    result["skipped_summaries"].items()
                ):
                    if i >= 5:
                        break
                    print(f"    - Researcher {researcher_id}: {reason}")

        if result.get("failed_summaries"):
            print(f"    Failed summaries: {len(result['failed_summaries'])}")
            if len(result["failed_summaries"]) <= 5:
                for researcher_id in result["failed_summaries"]:
                    print(f"    - Researcher {researcher_id}")
            else:
                print(f"    (showing first 5)")
                for researcher_id in result["failed_summaries"][:5]:
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
