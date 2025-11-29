# mapa-ciencia-unc

Data science project for UNC science mapping using scikit-learn, Jupyter notebooks, and seaborn.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

### Prerequisites

Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on Windows:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mapa-ciencia-unc
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Running the FastAPI App

To run the web application:

```bash
uvicorn mapa_ciencia_unc.main:app --reload
```

The app will be available at http://localhost:8000

### Docker Compose & Ngrok

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

### Running Jupyter Notebooks

After installation, start Jupyter:

```bash
jupyter notebook
```

Or use JupyterLab:

```bash
jupyter lab
```