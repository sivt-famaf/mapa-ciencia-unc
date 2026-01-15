# mapa-ciencia-unc

Data science project for UNC science mapping using scikit-learn, Jupyter notebooks, and seaborn.

## Table of Contents

- [Overview](#overview)
- [API Stack and Runtime](#api-stack-and-runtime)
- [Getting Started: The User Journey](#getting-started-the-user-journey)
  - [Understanding Your Data](#understanding-your-data)
  - [Loading Data into the System](#loading-data-into-the-system)
  - [Accessing the Application](#accessing-the-application)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Set up MongoDB Database](#set-up-mongodb-database)
  - [Option 1: Local MongoDB Installation](#option-1-local-mongodb-installation)
  - [Option 2: MongoDB with Docker (without Compose)](#option-2-mongodb-with-docker-without-compose)
- [Load Data to Database](#load-data-to-database)
- [Running the FastAPI Application](#running-the-fastapi-application)
- [Running with Docker Compose and Ngrok](#running-with-docker-compose-and-ngrok)
- [Database Operations](#database-operations)
- [Running Jupyter Notebooks](#running-jupyter-notebooks)

## Overview

The UNC Science Map is a web application that visualizes and analyzes research activity across the university. This system helps you explore researchers, their publications, projects, and collaborations through an interactive interface.

## API Stack and Runtime

- **Backend**: FastAPI with Beanie/Motor over MongoDB; app entrypoint is `mapa_ciencia_unc.main:app` served by uvicorn
- **Authentication**: HTTP Basic-style credentials to issue JWTs; protected routes depend on a bearer token
- **Frontend**: Server-rendered HTML+CSS+JS via Jinja templates plus static assets
- **Database**: MongoDB for storing researchers, articles, projects, and agreements

## Getting Started: The User Journey

### Understanding Your Data

As a user of this system, you'll start with research data in multiple formats spread across various files:

- **Articles** - CSV files containing publication data (authors, titles, abstracts, CUIT identifiers)
- **Projects and Calls** - CSV files with research project information and funding calls
- **Portfolios** - CSV files with researcher profile information
- **Agreements** - CSV files with institutional agreements data
- **Enrollment** - CSV files with researcher enrollment and affiliation data
- **Project Files** - PDF, DOC, DOCX files containing detailed project descriptions

Your goal is to get this data into the application's MongoDB database, where the web application can access and visualize it. During this pre-processing steps, the researcher is identified with the column "cuit".

### Loading Data into the System

The data loading process follows a pipeline approach, transforming raw CSV files into structured JSON data that gets uploaded to the database. This happens in stages:

**Stage 1: Preprocessing** - Clean and standardize your raw CSV files
**Stage 2: Filtering and Merging** - Filter by enrolled users and combine datasets
**Stage 3: Upload to Database** - Load the processed JSON files into MongoDB
**Stage 4: Project Files** (Optional) - Extract and upload detailed project descriptions

For detailed instructions on running each preprocessing script, including all command-line arguments and examples, see the **[scripts/README.md](scripts/README.md)** file.

Once the data is in MongoDB, the FastAPI application automatically picks it up and makes it available through the web interface and API endpoints.

---

## Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

**Required Software:**
- Python 3.9+
- MongoDB 5.0+ (installation covered below)
- [uv](https://github.com/astral-sh/uv) - Python package manager

**Install uv:**

On Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd mapa-ciencia-unc
```

2. **Create a virtual environment and install dependencies:**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

3. **Create environment configuration:**

Create a `.env` file in the project root with the following variables:

```bash
# MongoDB Configuration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=your_secure_password
MONGO_DB=mapa-ciencia-db
MONGO_HOST=localhost
MONGO_PORT=27017

# API Authentication
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your_api_password
JWT_SECRET=your_jwt_secret_key_here

# Application Settings
API_PORT=8000

# Model keys
GEMINI_API_KEY=
GEMINI_API_URL=
INTERNAL_SWAGGER_KEY=

# Ollama Configuration (for remote Ollama service)
# Base URL of the remote Ollama server (e.g., http://192.168.1.100:11434 or http://ollama-server.example.com:11434)
OLLAMA_HOST=https://chat.ccad.unc.edu.ar/
OLLAMA_API_KEY=

LOCAL_EMBEDDING_HOST=http://localhost:2904
```

## Set up MongoDB Database

You have two options for setting up MongoDB: local installation or Docker. We provide only
the instructions for Docker

**Run MongoDB container:**
```bash
docker run -d \
  --name mapa-mongo \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=your_secure_password \
  -e MONGO_INITDB_DATABASE=mapa-ciencia-db \
  -v mongo-data:/data/db \
  mongo:6.0
```

**Verify MongoDB is running:**
```bash
docker ps | grep mapa-mongo
```

**Access MongoDB shell:**
```bash
docker exec -it mapa-mongo mongosh -u admin -p your_secure_password --authenticationDatabase admin
```

**Stop/Start MongoDB container:**
```bash
docker stop mapa-mongo
docker start mapa-mongo
```

## Load Data to Database

Once MongoDB is running, you can load your research data using the preprocessing scripts.

**Step 1: Preprocess your raw data**

See the detailed documentation in [scripts/README.md](scripts/README.md) for complete instructions. Quick example:

```bash
export DATA_DIR=/path/to/your/data

# Stage 01: Preprocess raw CSV files
python scripts/01_1_preprocess_portfolios.py \
  --portfolios-file ${DATA_DIR}/raw_csv/portfolios.csv \
  --output-file ${DATA_DIR}/preprocessed_csv/portfolios.json

...

# Stage 02: Filter and merge
python scripts/02_1_filter_enrolled_users.py \
  --enrollment-file ${DATA_DIR}/preprocessed_csv/enrollments.json \
  --portfolios-file ${DATA_DIR}/preprocessed_csv/portfolios.json \
  --articles-file ${DATA_DIR}/preprocessed_csv/articles.json \
  --projects-file ${DATA_DIR}/preprocessed_csv/projects.json \
  --agreements-file ${DATA_DIR}/preprocessed_csv/agreements.json \
  --output-directory ${DATA_DIR}/merged_data
```

**Note**: Make sure the FastAPI application is running before executing the upload script (Stage 03).

## Running the FastAPI Application

Start the web application:

```bash
# Activate virtual environment if not already active
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the application
uvicorn mapa_ciencia_unc.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Running with Docker Compose and Ngrok

To deploy using compose and expose the port using ngrok:

1. Create a `.env` file with:
   - `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD`: Mongo admin credentials.
   - `MONGO_DB`: default database name (example: pri-db).
   - `MONGO_PORT=27018`: port exposed by `docker-compose.yml`.
   - `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD`: HTTP basic auth for the API.
   - `JWT_SECRET`: signing secret for issued tokens.
2. Start everything with `docker compose up --build`. If running on zx81 you may need to run `docker swarm leave (--force)` for the internal compose network to work.
3. Expose the backend from another terminal with:
   ```bash
   docker run --net=host -it -e NGROK_AUTHTOKEN=YOUR-NGROK-AUTHTOKEN ngrok/ngrok:latest http PORT
   ```
   Replace `PORT` with the backend port (default `8000`).


#### Database operations
##### Fresh start
In case you need reset the Mongo database (volume `mongo-data`) run `docker compose down` followed by `docker volume rm mapa-ciencia-unc_mongo-data` (`docker compose down -v` does both in one step.)

##### Drop table
To delete only one collection (researchers, for example), open a shell in the Mongo container and drop it:
```bash
docker compose exec mongo mongosh -u $MONGO_INITDB_ROOT_USERNAME -p $MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase admin $MONGO_DB --eval 'db.collectionName.drop()'
```
Replace `collectionName` with the collection you want to remove.

##### Backup table
Need a JSON snapshot instead? Use `mongoexport`:
```bash
docker compose exec mongo mongoexport \
  -u $MONGO_INITDB_ROOT_USERNAME \
  -p $MONGO_INITDB_ROOT_PASSWORD \
  --authenticationDatabase admin \
  -d $MONGO_DB \
  -c collectionName \
  --jsonArray > collectionName.json
```
This writes the selected collection into `collectionName.json` on the host machine.


### Running Jupyter Notebooks

After installation, start Jupyter:

```bash
jupyter notebook
```

Or use JupyterLab:

```bash
jupyter lab
```