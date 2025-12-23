# TODO add any handlers used to download data from drive

import html
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
import pandas as pd

## Data cleaners


def read_csv_file(
    local_path: str, separator: Optional[str] = ";", quotechar: Optional[str] = '"'
) -> pd.DataFrame:
    """
    Attempts to read a CSV file using several common encodings.
    Returns the loaded DataFrame or raises an error if all attempts fail.
    """

    # Common encodings
    encodings_to_try = ["utf-8", "latin-1", "cp1252"]

    # Try multiple encodings sequentially
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(
                local_path,
                sep=separator,
                quotechar=quotechar,
                encoding=enc,
                dtype=str,
                low_memory=False,
            )
            break
        except Exception as e:
            pass
    else:
        # If none worked, stop execution
        raise RuntimeError(
            "Could not read CSV with tried encodings. Inspect file manually."
        )

    return df


def clean_html_like(text: str) -> str:
    """
    Cleans HTML-like content, malformed tags, LaTeX fragments, unicode anomalies,
    and reference artifacts from a text field. Returns a normalized and readable string.
    """

    # Handle None safely
    if text is None:
        return text

    # Convert HTML entities (e.g., &nbsp;, &lt;) to their literal characters
    s = html.unescape(str(text))

    # Replace newlines with spaces so tags broken across lines are easier to match
    s = s.replace("\n", " ")

    # Attempt robust HTML parsing and extraction using BeautifulSoup
    try:
        s = BeautifulSoup(s, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        # Fallback: return the original text if parsing fails
        s = str(text)

    # Remove leftover tag fragments that might be missing the opening '<'
    s = re.sub(
        r"(?i)<?/?(?:font|p|div|span|br|i|b|strong|em|u|table|tr|td|tbody|thead|caption|a|sup|sub|center|blockquote|script|style)[^>]*>",
        " ",
        s,
    )

    # Remove angle brackets generically
    s = re.sub(r"<[^>]+>", " ", s)

    # Remove attribute-like residues that end without '>'
    s = re.sub(
        r'(?i)\b(?:font|p|div|span|br|i|b|strong|em|u|table|tr|td|a|center|sup|sub)\b[^"\'>]{0,80}"[^"]*"',
        " ",
        s,
    )
    s = re.sub(
        r'\b(?:size|face|align|style|class|id|href|src)\s*=\s*"[^"]*"\s*>?',
        " ",
        s,
        flags=re.IGNORECASE,
    )

    # Normalize unicode oddities
    UNICODE_FIXES = {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2009": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u223c": "~",
    }
    for bad, good in UNICODE_FIXES.items():
        s = s.replace(bad, good)

    # Remove LaTeX patterns
    LATEX_PATTERNS = [
        r"\$[^$]*\$",
        r"\\\([^\)]*\\\)",
        r"\\\[[^\]]*\\\]",
        r"\\text\{[^}]*\}",
        r"\\mathrm\{[^}]*\}",
        r"\\mathbf\{[^}]*\}",
        r"\\cite\{[^}]*\}",
        r"\\ref\{[^}]*\}",
        r"\\[a-zA-Z]+\s*",
    ]
    for pat in LATEX_PATTERNS:
        s = re.sub(pat, " ", s)

    # Remove {} brackets but keep text
    s = re.sub(r"\{([^{}]+)\}", r"\1", s)

    # Remove reference patterns
    s = re.sub(r"\[\d+\]", " ", s)
    s = re.sub(r"\( ?[Rr]ef\.? *\d+ ?\)", " ", s)
    s = re.sub(r"\( ?see [Ff]ig\.? *\d+ ?\)", " ", s)

    # Final normalization
    s = re.sub(r">+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s


def read_data_file(file_path: Path, separator: str = ",") -> pd.DataFrame:
    """
    Read data file supporting multiple formats (CSV, Parquet, JSON).

    Args:
        file_path: Path to the data file
        separator: Separator for CSV files (default: ",")

    Returns:
        DataFrame with the loaded data

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    # Read file based on extension
    if file_path.suffix == ".csv":
        df = read_csv_file(file_path, separator=separator)
    elif file_path.suffix == ".parquet":
        df = pd.read_parquet(file_path)
    elif file_path.suffix == ".json":
        df = pd.read_json(file_path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    return df


def save_output_by_extension(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save the preprocessed data to the output file.

    Args:
        df: Preprocessed dataframe
        output_path: Path where to save the output file
    """
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine output format based on file extension
    if output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    elif output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".json":
        df.to_json(output_path, orient="records", lines=True)
    else:
        # Default to CSV
        df.to_csv(output_path, index=False)

    print(f"\nOutput saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")
