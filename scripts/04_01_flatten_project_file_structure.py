"""
This process flattens the nested project file structure by moving all files from subdirectories
to a single target directory. It searches through each subdirectory recursively and
attempts to find a descriptive file for each project, it will look for files in the following order:
1. File containting the word 'plan' in its name. (plan de trabajo)
2. File containting the word 'fundamentac' in its name. (fundamentación)
3. File containting the word 'justific' in its name. (justificación)
4. File containting the word 'proy_a_desarrollar' in its name. (proyecto a desarrollar)

It renames files to the following format:
<cuil>_<codigo_tramite>_<original_filename>.<extension>

These extensions are considered valid: '.pdf', '.doc', '.docx', '.rtf', '.odt', '.rar'

If no descriptive file is found, it will skip that project.
It does not avoid duplicate files.

Inputs:
 - A source directory with nested subdirectories.

Outputs:
 - A target directory with all files flattened. Will create the target directory if it does not exist

Example usage:
python scripts/04_01_flatten_project_file_structure.py \
    --source-dir path/to/nested/projects \
    --target-dir path/to/flattened/projects
"""

import os
import pathlib
import shutil
import argparse


def find_document_files(directory_path: str) -> list[str]:
    """
    Recursively searches a directory for files with the extensions:
    .pdf, .doc, .docx, .rtf, .odt, .rar

    Args:
        directory_path: The root directory to start the search from.

    Returns:
        A list of full paths for all found files.
    """
    found_files = []
    target_extensions = [".pdf", ".doc", ".docx", ".rtf", ".odt", ".rar"]
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            ext = pathlib.Path(file_name).suffix
            if ext.lower() in target_extensions:
                full_path = os.path.join(root, file_name)
                found_files.append(full_path)

    return found_files


def search_dir_by_substring(path: str, subdirs: list[str], substring: str) -> list[str]:
    matching_subdirs = [d for d in subdirs if substring in d.upper()]
    if matching_subdirs:
        search_path = os.path.join(path, matching_subdirs[0])
        files_in_search_path = find_document_files(search_path)
        if files_in_search_path:
            return files_in_search_path[0]

    return None


def process_project_subdir(project_subdir_path: str):
    subdirs = os.listdir(project_subdir_path)
    subdirs = [d for d in subdirs if d != ".DS_Store"]

    substrings = ["PLAN", "FUNDAMENTA", "JUSTIFICA"]
    for substring in substrings:
        found_file = search_dir_by_substring(project_subdir_path, subdirs, substring)
        if found_file:
            return found_file

    return None


def process_cuil_subdir(cuil: str, base_path: str):
    codigos_tramites = os.listdir(os.path.join(base_path, cuil))
    found = {}
    for codigo_tramite in codigos_tramites:
        project_subdir_path = os.path.join(base_path, cuil, codigo_tramite)
        found_file = process_project_subdir(project_subdir_path)
        found[codigo_tramite] = found_file

    return found


def process_input_directory(input_dir: str):
    results = {}
    cuils = os.listdir(input_dir)
    for cuil in cuils:
        cuil_result = process_cuil_subdir(cuil, base_path=input_dir)
        results[cuil] = cuil_result

    return results


def flatten_dir(input_dir: str, target_dir: str):
    os.makedirs(target_dir, exist_ok=True)
    files_dict = process_input_directory(input_dir)

    cuils = set(files_dict.keys())
    codigos_tramite = set([k for cuil in cuils for k in files_dict[cuil].keys()])

    print("CUILs found:", len(cuils))
    print("Codigos tramite found:", len(codigos_tramite))

    processed_projects = set()
    for cuil, project_dict in files_dict.items():
        for codigo_tramite, project_file in project_dict.items():
            if project_file:
                file_name = pathlib.Path(project_file).name
                new_project_file_name = f"{cuil}_{codigo_tramite}_{file_name}"
                new_project_file_path = os.path.join(target_dir, new_project_file_name)
                shutil.copy2(project_file, new_project_file_path)
                processed_projects.add(codigo_tramite)

    print("Processed projects:", len(processed_projects))
    print("Failed projects:", len(codigos_tramite) - len(processed_projects))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Flatten nested project file structure into a single directory."
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        required=True,
        help="Path to the source directory with nested project files.",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        required=True,
        help="Path to the target directory for flattened project files.",
    )

    args = parser.parse_args()
    flatten_dir(input_dir=args.source_dir, target_dir=args.target_dir)
