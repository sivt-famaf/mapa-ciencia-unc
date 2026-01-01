"""
Script to upload bulk research topics to the database from a JSON file.

This script reads a JSON file containing research topic data and uploads them
to the database using the bulk research topics endpoint.

Input JSON Format:
    The file should be a JSON array containing topic objects:
    [
        {
            "topic_id": 7,
            "keywords": ["economy", "development"],
            "researchers": ["20337008268", "27273268885"],
            "size": 2,
            "name": "Economía Aplicada",
            "description": "Esta área se...",
            "embedding": [0.1, 0.2, 0.3, ...]
        }
    ]

    Notes:
    - topic_id: Integer identifier for the topic, but not used
    - researchers: List of CUIT identifiers
    - size: Number of researchers in the topic, not used

Arguments:
    --username: Username for API authentication
    --password: Password for API authentication
    --api-url: Base URL for the API (e.g., http://localhost:8000)
    --topics-file: Path to the JSON file containing topics
    --topic-tag: Tag to assign to all topics (e.g., "bertopic-sample15")
    --summary-tag: Summary tag for topics (e.g., "user_academic_temp05")
    --summary-model: Summary model name (e.g., "gemini-2.5-pro")
    --embedding-tag: Embedding tag for topics (e.g., "embeddings_v1_avg")
    --embedding-model: Embedding model name (e.g., "gemini-embedding-001")
    --overwrite: Whether to overwrite existing topics with the same name (flag, default: False)

Example usage:
    python scripts/05_4_upload_bulk_research_topics.py \
        --username admin \
        --password secret \
        --api-url http://localhost:8000 \
        --topics-file path/to/topics.json \
        --topic-tag bertopic-sample15 \
        --summary-tag user_academic_temp05 \
        --summary-model gemini-2.5-pro \
        --embedding-tag embeddings_v1_avg \
        --embedding-model gemini-embedding-001 \
        --overwrite
"""

import json
import argparse
import requests
import time


LOGIN_ENDPOINT = "/login"
BULK_TOPICS_ENDPOINT = "/api/research_topics/upload/bulk"


def get_token(username: str, password: str, url: str) -> str:
    """
    Get an authentication token from the API.
    """
    response = requests.post(
        url,
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def upload_topics(
    topics: list,
    topic_tag: str,
    summary_tag: str,
    summary_model: str,
    embedding_tag: str,
    embedding_model: str,
    api_url: str,
    headers: dict,
    overwrite: bool = False,
) -> dict:
    """
    Upload research topics to the API.
    """
    payload = {
        "summary_tag": summary_tag,
        "summary_model": summary_model,
        "embedding_tag": embedding_tag,
        "embedding_model": embedding_model,
        "tag": topic_tag,
        "topics": topics,
        "overwrite": overwrite,
    }

    response = requests.post(
        api_url + BULK_TOPICS_ENDPOINT,
        headers=headers,
        json=payload,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"\nError uploading topics: {e}")
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        raise
    return response.json()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload research topics to the database via API."
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
        "--topics-file",
        type=str,
        required=True,
        help="Path to the JSON file with topics",
    )
    parser.add_argument(
        "--topic-tag",
        type=str,
        required=True,
        help="Tag to assign to all topics (e.g., bertopic-sample15)",
    )
    parser.add_argument(
        "--summary-tag",
        type=str,
        required=True,
        help="Summary tag (e.g., user_academic_temp05)",
    )
    parser.add_argument(
        "--summary-model",
        type=str,
        required=True,
        help="Summary model name (e.g., gemini-2.5-pro)",
    )
    parser.add_argument(
        "--embedding-tag",
        type=str,
        required=True,
        help="Embedding tag (e.g., embeddings_v1_avg)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        required=True,
        help="Embedding model name (e.g., gemini-embedding-001)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing topics with the same name",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_time = time.time()

    # Authenticate
    print("Authenticating...")
    token = get_token(args.username, args.password, url=args.api_url + LOGIN_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}

    # Load topics from file
    print(f"Loading topics from {args.topics_file}...")
    with open(args.topics_file, "r", encoding="utf-8") as f:
        topics = json.load(f)

    print(f"Found {len(topics)} topics")

    # Validate topics and filter out invalid ones
    valid_topics = []
    skipped_topics = []
    required_fields = [
        "topic_id",
        "keywords",
        "size",
        "name",
        "embedding",
        "researchers",
    ]

    for i, topic in enumerate(topics):
        missing_fields = [field for field in required_fields if field not in topic]

        # Check if embedding is empty
        if "embedding" in topic and not topic["embedding"]:
            missing_fields.append("embedding (empty)")

        if missing_fields:
            skipped_topics.append(
                {
                    "index": i,
                    "name": topic.get("name", "unknown"),
                    "topic_id": topic.get("topic_id", "unknown"),
                    "missing": missing_fields,
                }
            )
        else:
            topic["researchers"] = [str(x) for x in topic["researchers"]]
            valid_topics.append(topic)

    if skipped_topics:
        print(f"\nSkipped {len(skipped_topics)} invalid topics:")
        for skipped in skipped_topics:
            print(
                f"  - {skipped['name']} (ID: {skipped['topic_id']}, index: {skipped['index']}): Missing fields: {', '.join(skipped['missing'])}"
            )

    print(f"\nProceeding with {len(valid_topics)} valid topics")

    if not valid_topics:
        print("No valid topics to upload. Exiting.")
        exit(1)

    # Upload topics
    print("Uploading topics...")

    result = upload_topics(
        topics=valid_topics,
        topic_tag=args.topic_tag,
        summary_tag=args.summary_tag,
        summary_model=args.summary_model,
        embedding_tag=args.embedding_tag,
        embedding_model=args.embedding_model,
        api_url=args.api_url,
        headers=headers,
        overwrite=args.overwrite,
    )

    end_time = time.time()

    # Print results
    print(f"\n=== Summary ===")
    print(f"Created: {result['created']}")
    print(f"Failed: {len(result['failed'])}")
    if result["failed"]:
        print("\nFailed topics:")
        for failed in result["failed"]:
            print(f"  - {failed['name']} (ID: {failed['topic_id']}): {failed['error']}")
    print(f"Total time: {end_time - start_time:.2f} seconds")
