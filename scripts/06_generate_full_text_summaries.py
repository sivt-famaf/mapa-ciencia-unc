"""
Generate full-text summaries for all researchers in the database.

Queries all researchers and generates full-text summaries using the
full-text template (no LLM processing).

Inputs:
    - API URL, username, and password for authentication
    - Tag to assign to generated summaries
    - Prompt name for the template (e.g., "v2/full_description")

Example usage:
python scripts/06_generate_full_text_summaries.py \
    --api-url http://localhost:8000 \
    --username admin \
    --password secret \
    --tag full-text-v1 \
    --prompt-name v2/full_description
"""

import argparse
import requests
import time


LOGIN_ENDPOINT = "/login"
RESEARCHERS_ENDPOINT = "/api/researchers"
GENERATE_SUMMARY_ENDPOINT = "/api/summaries/generate"


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


def get_all_researchers(api_url, headers):
    """
    Fetch all researchers from the database.
    """
    response = requests.get(
        api_url + RESEARCHERS_ENDPOINT,
        headers=headers,
        params={"limit": 10},
    )
    response.raise_for_status()
    return response.json()


def generate_summary(researcher_id, tag, prompt_name, api_url, headers):
    """
    Generate a full-text summary for a single researcher.
    """
    payload = {
        "researcher_id": researcher_id,
        "model": "full-text",
        "tag": tag,
        "prompt_name": prompt_name,
    }

    response = requests.post(
        api_url + GENERATE_SUMMARY_ENDPOINT,
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate full-text summaries for all researchers."
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
        "--tag",
        type=str,
        required=True,
        help="Tag to assign to generated summaries",
    )
    parser.add_argument(
        "--prompt-name",
        type=str,
        default="v2/full_description",
        help="Name of the prompt template (default: v2/full_description)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_time = time.time()

    # Authenticate
    print("Authenticating...")
    token = get_token(args.username, args.password, url=args.api_url + LOGIN_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch all researchers
    print("Fetching researchers...")
    researchers = get_all_researchers(args.api_url, headers)
    print(f"Found {len(researchers)} researchers")

    # Generate summaries
    successful = 0
    failed = 0
    for i, researcher in enumerate(researchers, 1):
        researcher_id = researcher["_id"]
        try:
            print(f"[{i}/{len(researchers)}] Generating summary for {researcher_id}...")
            generate_summary(
                researcher_id, args.tag, args.prompt_name, args.api_url, headers
            )
            successful += 1
        except Exception as e:
            print(f"  ERROR: Failed to generate summary: {e}")
            failed += 1

    end_time = time.time()
    print(f"\n=== Summary ===")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total time: {end_time - start_time:.2f} seconds")
