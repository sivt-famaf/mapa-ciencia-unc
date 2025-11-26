# TODO add any handlers used to download data from drive

import html
import re
from typing import Optional

from bs4 import BeautifulSoup
import pandas as pd

## Data cleaners


def read_csv_file(
    local_path: str, separator: Optional[str] = ";",
    quotechar: Optional[str] = '"'
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
                local_path, sep=separator,
                quotechar=quotechar,
                encoding=enc, dtype=str, low_memory=False
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
    s = s.replace('\n', ' ')

    # Attempt robust HTML parsing and extraction using BeautifulSoup
    try:
        s = BeautifulSoup(s, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        # Fallback: return the original text if parsing fails
        s = str(text)

    # Remove leftover tag fragments that might be missing the opening '<'
    s = re.sub(
        r'(?i)<?/?(?:font|p|div|span|br|i|b|strong|em|u|table|tr|td|tbody|thead|caption|a|sup|sub|center|blockquote|script|style)[^>]*>',
        ' ',
        s
    )

    # Remove angle brackets generically
    s = re.sub(r'<[^>]+>', ' ', s)

    # Remove attribute-like residues that end without '>'
    s = re.sub(
        r'(?i)\b(?:font|p|div|span|br|i|b|strong|em|u|table|tr|td|a|center|sup|sub)\b[^"\'>]{0,80}"[^"]*"',
        ' ',
        s
    )
    s = re.sub(r'\b(?:size|face|align|style|class|id|href|src)\s*=\s*"[^"]*"\s*>?', ' ', s, flags=re.IGNORECASE)

    # Normalize unicode oddities
    UNICODE_FIXES = {
        "\u00A0": " ",
        "\u202F": " ",
        "\u2009": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u223C": "~",
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
    s = re.sub(r'>+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    return s