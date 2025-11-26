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

### Running Jupyter Notebooks

After installation, start Jupyter:

```bash
jupyter notebook
```

Or use JupyterLab:

```bash
jupyter lab
```