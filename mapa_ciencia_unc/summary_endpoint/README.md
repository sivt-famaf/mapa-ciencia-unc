# **Summary Endpoint Directory**

This repository provides a FastAPI service for generating researcher summaries using Google Gemini large language models.

The service takes as input a dataset in JSON, CSV, or Parquet format containing information about researcher profiles (articles, calls, projects, agreements, PDFs), and dynamically renders Jinja-based prompts to generate structured outputs.

## **Structure**
``` 
summary_endpoint/
│── models/
│   └──schemas.py
│── routers/
│   └── summaries_router.py
│── services/
│   ├── dataset_loader.py
│   ├── prompt_builder.py
│   └── summary_generator.py
│── tests/
│   └── test_generate_summaries.py
│── utils/
│   ├── security.py
│   └── swagger_docs.py
│── __init__.py
│── .env
│── config.py
│── main.py
``` 

## **Core Components**

### **1. `main.py` – FastAPI App Initialization**

``` 
app = FastAPI(title="Mapa Ciencia UNC - Summary API")
app.include_router(summaries_router, prefix="/summaries", tags=["Summaries"])
``` 
This file creates the FastAPI application, mounts the router and defines global metadata.

### **2. `config.py` – Configuration & Environment Management**

Loads `.env` variables, directories for templates and keys for Gemini and internal security.

Key variables:
``` 
GEMINI_API_KEY
GEMINI_API_URL
INTERNAL_SWAGGER_KEY
```

### **3. `models/schemas.py` – Request Schemas**

Defines the SummaryRequest Pydantic model for request validation. 

Request format:
``` 
{
  "dataset_path": str,
  "limit": int,
  "include_articles": bool,
  "include_calls": bool,
  "include_projects": bool,
  "include_convenios": bool,
  "include_pdfs": bool,
  "system_name": str,
  "prompt_name": str,
}
``` 

### **4. `routers/summaries_router.py` – Main Endpoint**

The `POST /summaries/generate-summaries` route is responsible for validating the incoming request header through middleware, loading the appropriate dataset via the service layer, and selecting the correct templates based on the provided names. For each row in the dataset, the route generates a summary and returns a structured list of results. Each result includes an id and a summary object containing a brief description, a profile, and a list of areas, as shown in the example response below:

``` 
{
  "results": [
    {
      "id": "...",
      "summary": {
        "brief": "...",
        "profile": "...",
        "areas": ["...", "..."]
      }
    }
  ]
}
``` 

### **5. `services/dataset_loader.py` – Dataset Ingestion**

This file handles dataset ingestion by reading input files and returning a pandas DataFrame, while raising errors when the file format is invalid. It supports CSV, JSON, and Parquet formats, and automatically selects the appropriate loader based on the file’s extension.

### **6. `services/prompt_builder.py` – Template Rendering (Jinja2)**

This component renders two templates: a system instruction and a user prompt. It returns a tuple containing the generated system instruction and prompt. Its purpose is to dynamically populate templates and enable customizable system and user prompts.

### **7. `services/summary_generator.py` – Gemini Integration**

This core module is responsible for loading the required templates, constructing the structured schema used by Gemini, sending the generated prompt to the model, and parsing the resulting JSON response. 

Schema enforced:
``` 
{
  "brief": "string",
  "profile": "string",
  "areas": ["string"]
}
``` 
Returns a Python dictionary representing the parsed output.

### **8. `utils/security.py` – Internal API Protection**

The validation process ensures that the X-Internal-Key header is present and matches the expected environment key. If the header is missing, the request results in an HTTP 422 error, while an invalid key triggers an HTTP 403 response.

### **9. `utils/swagger_docs.py` – Swagger Text**

Adds a clean description to the API docs.

### **10. `tests/test_integration_gemini.py` – Integration Test**

This test validates the entire flow, including dataset loading, prompt rendering, the Gemini API response, and the final JSON schema. 

Run tests: 
``` 
pytest .
``` 

## **Template System**
Expected directory structure with JINJA files:
``` 
prompts/
   profile_summary/
      system/
         ...
      user/
         ...
``` 

## **Running the API**

### **1. Start the server**

Start the FastAPI application with Uvicorn:
``` 
uvicorn summary_endpoint.main:app --reload
```
This runs the service in development mode with auto-reload enabled.

### **2. Access Swagger UI**
Open your browser and navigate to:
``` 
http://localhost:8000/docs
``` 
From here you can explore and test the generate-summaries endpoint, but remember that it requires an internal key (see next steps).

### **3. Call the endpoint**
The endpoint accepts POST requests at:
``` 
POST /summaries/generate-summaries
``` 
This route is protected and only accessible when providing the correct internal header.

**Request sample:**
``` 
{
  "dataset_path": "data/researchers.json",
  "limit": 10,
  "include_articles": False,
  "include_calls": False,
  "include_projects": False,
  "include_convenios": False,
  "include_pdfs": False,
  "system_name": "v1/system_instruction_1",
  "prompt_name": "v1/prompt_1",
}
``` 

**Required header:**
This endpoint requires an internal authentication key:
``` 
x-internal-key: <INTERNAL_SWAGGER_KEY>
``` 
INTERNAL_SWAGGER_KEY must be configured in your .env file.

**Response example:**
``` 
{
  "results": [
    {
      "id": 123,
      "summary": {
        "brief": "Researcher specializing in physics...",
        "profile": "The researcher has extensive experience in...",
        "areas": ["Physics", "Materials Science"]
      }
    }
  ]
}
``` 
Each entry includes the original researcher id and a summary object containing a structured JSON response generated by Gemini.

## **Client examples**

### **cURL Example**

Use this command to call the endpoint directly from the terminal:
``` 
curl -X POST "http://localhost:8000/summaries/generate-summaries" \
  -H "Content-Type: application/json" \
  -H "x-internal-key: <INTERNAL_SWAGGER_KEY>" \
  -d '{
        "dataset_path": "data/researchers.json",
        "limit": 5,
        "include_articles": false,
        "include_calls": false,
        "include_projects": false,
        "include_convenios": false,
        "include_pdfs": false,
        "system_name": "v1/system_instruction_1",
        "prompt_name": "v1/prompt_1"
      }'
``` 

### **Python Client Example**

A simple Python script using requests to call the API:
``` 
import requests
import json

API_URL = "http://localhost:8000/summaries/generate-summaries"
INTERNAL_KEY = "<INTERNAL_SWAGGER_KEY>"

payload = {
    "dataset_path": "data/researchers.json",
    "limit": 5,
    "include_articles": False,
    "include_calls": False,
    "include_projects": False,
    "include_convenios": False,
    "include_pdfs": False,
    "system_name": "v1/system_instruction_1",
    "prompt_name": "v1/prompt_1"
}

headers = {
    "Content-Type": "application/json",
    "x-internal-key": INTERNAL_KEY
}

response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

if response.status_code == 200:
    print("Success:")
    print(json.dumps(response.json(), indent=2))
else:
    print("Error:", response.status_code, response.text)
``` 