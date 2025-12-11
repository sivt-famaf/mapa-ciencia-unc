import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from ..main import app
from ..config import INTERNAL_SWAGGER_KEY

client = TestClient(app)


# -----------------------
# Helper test dataset
# -----------------------

def create_temp_json(tmp_path):
    """Create a temporary dataset file for the tests."""
    data = [
        {"id": 1, "info_completa": "Investigador en IA, trabaja en modelos generativos."},
        {"id": 2, "info_completa": "Especialista en análisis de datos y estadística aplicada."}
    ]

    file_path = tmp_path / "dataset.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


# -----------------------
# Mock for summary generator
# -----------------------

def fake_summary_function(info, system_instruction_path, prompt_path, model_name="gemini-2.5-flash"):
    """
    Mock replacement for generate_researcher_summary.
    """
    return {
        "brief": f"Resumen generado ficticio para: {info[:20]}...",
        "profile": "xxx",
        "areas": ["IA", "datos"]
    }


# -----------------------
# Tests
# -----------------------

def test_generate_summaries_success(tmp_path, monkeypatch):
    """
    Test: Endpoint returns summaries correctly using mock Gemini.
    """

    # 1. Create fake dataset
    dataset_path = create_temp_json(tmp_path)

    # 2. Patch the summary generator to avoid real API calls
    monkeypatch.setattr(
        "mapa_ciencia_unc.summary_endpoint.services.summary_generator.generate_researcher_summary",
        fake_summary_function
    )


    # 3. Prepare request
    payload = {
        "dataset_path": str(dataset_path),
        "limit": 2,
        "include_articles": False,
        "include_calls": False,
        "include_projects": False,
        "include_convenios": False,
        "include_pdfs": False,
        "system_name": "v1/system_instruction_1",
        "prompt_name": "v1/prompt_1",
    }

    headers = {
        "x-internal-key": INTERNAL_SWAGGER_KEY
    }

    # 4. Call endpoint
    response = client.post("/summaries/generate-summaries", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Validate structure
    assert "results" in data
    assert len(data["results"]) == 2

    for item in data["results"]:
        assert "id" in item
        assert "summary" in item
        assert "brief" in item["summary"]
        assert "profile" in item["summary"]
        assert "areas" in item["summary"]


def test_missing_internal_key(tmp_path):
    """
    Test: Endpoint must reject requests without internal key.
    """
    
    dataset_path = create_temp_json(tmp_path)

    payload = {
        "dataset_path": str(dataset_path),
        "limit": 2,
        "include_articles": False,
        "include_calls": False,
        "include_projects": False,
        "include_convenios": False,
        "include_pdfs": False,
        "system_name": "v1/system_instruction_1",
        "prompt_name": "v1/prompt_1",
    }

    response = client.post("/summaries/generate-summaries", json=payload)

    assert response.status_code == 422  # Missing required header


def test_invalid_internal_key(tmp_path):
    """
    Test: Endpoint must reject requests with invalid API key.
    """
    
    dataset_path = create_temp_json(tmp_path)

    payload = {
        "dataset_path": str(dataset_path),
        "prompt_name": "v1/prompt_1",
        "system_name": "v1/system_instruction_1"
    }

    headers = {
        "x-internal-key": "wrong-key"
    }

    response = client.post("/summaries/generate-summaries", json=payload, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid internal key"