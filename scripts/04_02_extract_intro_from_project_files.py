"""
This process attempts to open all files in a given directory and extract the introductory text
from each project file. It saves the extracted intros into a json file for further use.

By default, 500 are extracted from each file.
These extensions are considered valid: '.pdf', '.doc', '.docx', '.rtf', '.odt', '.rar'
If a file cannot be opened or no intro can be extracted, it will skip that file.
Inputs:
    - A source directory with project files.
Outputs:
    - A json file with the extracted intros, where keys are the file names and values are the extracted text.

Example usage:
python processes/extract_intro_from_project_files.py \
    --source-dir path/to/project/files \
    --output-file path/to/output/intros.json \
    --num-words 500

Requires:
  
  python packages:
    - pymupdf (https://pymupdf.readthedocs.io/en/latest/)
    - python-docx (https://python-docx.readthedocs.io/en/latest/)
    - striprtf (https://pypi.org/project/striprtf/)
    - odf (https://pypi.org/project/odfpy/)
    - rarfile (https://rarfile.readthedocs.io/#)
  
  system packages:
    - antiword (for .doc files)
    - unrar/unar/7zip/p7zip (backend for rarfile https://rarfile.readthedocs.io/#)
"""

import argparse
import os
import json
import pathlib
import subprocess
import re
import regex
import unicodedata
from io import BytesIO

import docx
import pymupdf
import rarfile
from striprtf.striprtf import rtf_to_text
from odf import teletype
from odf import text as odf_text
from odf.opendocument import load


def parse_entire_text(
    text: str, first_n_words: int = 500, offset_match: str = None
) -> str:
    while "  " in text:
        text = text.replace("  ", " ")

    text = text.replace("\n", " ").replace("\t", " ")

    text = re.sub(r"\(.*?\)", "", text)
    text = text.strip()

    if offset_match:
        match = re.search(re.escape(offset_match), text, re.IGNORECASE)
        if match:
            start_index = match.end()
            text = text[start_index:].strip()

    text = " ".join(text.split()[:first_n_words])
    return text


def extract_pdf_text(file_path, from_bytes=False):
    try:
        if from_bytes:
            doc = pymupdf.open(stream=file_path, filename="file.pdf")
        else:
            doc = pymupdf.open(file_path)  # open a document

        text = ""
        for page in doc[:1]:  # iterate the document pages
            text += page.get_text()  # get plain text (is in UTF-8)
        return clean_string_with_unicode_properties(text)
    except Exception as e:
        print(f"Error extracting PDF file {file_path}: {e}")
        return None


def extract_docx_text(file_path, from_bytes=False):
    if from_bytes:
        file_stream = BytesIO(file_path)
        doc = docx.Document(file_stream)
    else:
        doc = docx.Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + " "
    return text


def extract_doc_text(file_path):
    result = subprocess.run(["antiword", str(file_path)], stdout=subprocess.PIPE)
    res = result.stdout.decode("utf-8")
    if res == "":
        try:
            res = extract_rtf_text(file_path)
        except Exception as e:
            print(
                f"Error extracting DOC file {file_path} with antiword and rtf fallback: {e}"
            )
            res = None

    return res


def extract_rtf_text(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return rtf_to_text(text)


def extract_odt_text(file_path):
    textdoc = load(file_path)
    allparas = textdoc.getElementsByType(odf_text.P)
    text = ""
    for para in allparas:
        text += teletype.extractText(para) + " "
    return text


def clean_string_with_unicode_properties(text):
    normalized = unicodedata.normalize("NFKD", text)
    cleaned = regex.sub(r"[\p{Cc}\p{Zs}]+", " ", normalized)
    return " ".join(cleaned.strip().split())


def extract_rar_text(file_path):
    rf = rarfile.RarFile(file_path)
    if len(rf.infolist()) == 0:
        return None

    if len(rf.infolist()) >= 1:
        plan_file = rf.infolist()[0]
        for f in rf.infolist():
            if "PLAN" in f.filename.upper():
                plan_file = f

    try:
        ext = pathlib.Path(plan_file.filename).suffix.lower()
        if ext == ".pdf":
            bytes_pdf = rf.read(plan_file)
            return extract_pdf_text(bytes_pdf, from_bytes=True)
        elif ext == ".docx":
            bytes_docx = rf.read(plan_file)
            return extract_docx_text(bytes_docx, from_bytes=True)
        else:
            return None
    except Exception as e:
        print(f"Error extracting {file_path}: {e}")
        return None


def extract_content_from_file(file_path: str, first_n_words: int = 500) -> str:
    try:
        path = pathlib.Path(file_path)
        suffix = path.suffix.lower()

        match suffix:
            case ".pdf":
                text = extract_pdf_text(file_path)
            case ".docx":
                text = extract_docx_text(file_path)
            case ".doc":
                text = extract_doc_text(file_path)
            case ".rtf":
                text = extract_rtf_text(file_path)
            case ".odt":
                text = extract_odt_text(file_path)
            case ".rar":
                text = extract_rar_text(file_path)
            case _:
                print(f"Unknown file type: {file_path}")
                return None

        offset_match = None
        if "PROY_A_DESARROLLAR" in file_path.upper():
            offset_match = "CARACTERÍSTICAS DEL PROYECTO"

        parsed_text = parse_entire_text(
            text, first_n_words=first_n_words, offset_match=offset_match
        )

        return parsed_text
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None


def process_directory(source_dir: str, output_file: str, num_words: int = 500):
    results = {}
    files = os.listdir(source_dir)

    print(f"Found {len(files)} files in source directory.")

    for file_name in files:
        ext = pathlib.Path(file_name).suffix
        if not ext.lower() in [".pdf", ".doc", ".docx", ".rtf", ".odt", ".rar"]:
            print(f"Skipping unsupported file: {file_name}")
            continue

        full_path = os.path.join(source_dir, file_name)
        try:
            intro_text = extract_content_from_file(full_path, first_n_words=num_words)
        except Exception as e:
            print(f"Error extracting intro from {file_name}: {e}, skipping.")
            continue

        if intro_text:
            results[file_name] = intro_text

    print(f"Extracted intros from {len(results)} files.")
    print(f"Failed to extract intros from {len(files) - len(results)} files.")

    with open(output_file, "w") as out_f:
        json.dump(results, out_f, ensure_ascii=False, indent=2)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Extract introductory text from project files in a directory."
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        required=True,
        help="Path to the source directory containing project files.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        required=True,
        help="Path to the output JSON file to save extracted intros.",
    )
    parser.add_argument(
        "--num-words",
        type=int,
        default=500,
        help="Number of words to extract from the beginning of each file.",
    )

    args = parser.parse_args()

    process_directory(
        source_dir=args.source_dir,
        output_file=args.output_file,
        num_words=args.num_words,
    )
