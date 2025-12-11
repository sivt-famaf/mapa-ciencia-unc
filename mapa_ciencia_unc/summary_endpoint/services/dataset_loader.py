import pandas as pd
from pathlib import Path

def load_dataset(path: Path) -> pd.DataFrame:
    """
    Load dataset from JSON, CSV or Parquet.

    Parameters
    ----------
    path : Path

    Returns
    -------
    pd.DataFrame
    """
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        return pd.read_json(path, lines=False)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)

    raise ValueError(f"Unsupported dataset format: {suffix}")