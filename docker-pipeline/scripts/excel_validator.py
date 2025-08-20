#!/usr/bin/env python3

import argparse
import json
import requests
import subprocess
import sys

from pathlib import Path
from typing import Any
import csv
from datetime import datetime

from scripts.util import wait_for_service, wait_for_container_health

DICTIONARY_NAME = "CancerModels_Dictionary"
DICTIONARY_VERSION = "2.2"
LECTERN_URL = "http://localhost:3000"
VALIDATOR_URL = "http://localhost:3009/validation/upload-excel"

OUTPUT_DIRECTORY_NAME = "output"


def init_validator():
    """
    Starts lecturesDb and lectern containers, creates the dictionary if missing,
    and finally starts pdcm-lectern-validator container.
    """

    compose_dir = Path(__file__).parent.parent

    # Step 1: Start lecternDb and lectern only
    print("🚀 Starting lecternDb and lectern containers...")
    try:
        subprocess.run(
            ["docker-compose", "up", "-d", "lecternDb", "lectern"],
            cwd=compose_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ Failed to start lecternDb and lectern: {e}")

    # Step 2: Wait for Lectern to be healthy (check HTTP 200)
    wait_for_service(LECTERN_URL)

    # Step 3: Create dictionary if it does not exist
    from scripts.excel_validator import (
        create_dictionary,
    )  # ensure this imports your logic above

    if dictionary_exists(LECTERN_URL, DICTIONARY_NAME, DICTIONARY_VERSION):
        print(
            f"Dictionary {DICTIONARY_NAME} version {DICTIONARY_VERSION} already exists"
        )
    else:
        create_dictionary(LECTERN_URL, DICTIONARY_VERSION)

    # Step 4: Start pdcm-lectern-validator container
    print("🚀 Starting pdcm-lectern-validator container...")
    try:
        subprocess.run(
            ["docker-compose", "up", "-d", "pdcm-lectern-validator"],
            cwd=compose_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ Failed to start pdcm-lectern-validator: {e}")
    wait_for_container_health("docker-pipeline-pdcm-lectern-validator-1")
    print("✅ Validator stack initialized successfully.")


def init_validator_originl():
    """
    Starts the Docker services needed for the Excel validator
    (e.g., MongoDB, Lectern, PDCM validator).
    """
    print("🚀 Starting docker containers for the validation process...")

    compose_dir = Path(
        __file__
    ).parent.parent  # adjust to location of docker-compose.yml

    try:
        subprocess.run(["docker-compose", "up", "-d"], cwd=compose_dir, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ Failed to start validator services: {e}")

    print("✅ Validator services started successfully.")

    if dictionary_exists(LECTERN_URL, DICTIONARY_NAME, DICTIONARY_VERSION):
        print(
            f"Dictionary {DICTIONARY_NAME} version {DICTIONARY_VERSION} already exists"
        )
    else:
        create_dictionary(LECTERN_URL, DICTIONARY_VERSION)


def dictionary_exists(lectern_url: str, name: str, version: str) -> bool:
    """
    Checks if a dictionary with the given name and version already exists in Lectern.

    Args:
        lectern_url (str): Base URL for the Lectern service (e.g., http://localhost:3000)
        name (str): Dictionary name
        version (str): Dictionary version

    Returns:
        bool: True if the dictionary exists, False otherwise.
    """
    endpoint = f"{lectern_url}/dictionaries"

    print(f"Trying to create dictionary {name} version {version} in Lectern ...")

    try:
        response = requests.get(endpoint)
        response.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f"❌ Failed to query dictionaries from Lectern: {e}")

    try:
        dictionaries = response.json()
    except ValueError:
        sys.exit("❌ Invalid JSON response from Lectern service.")

    for d in dictionaries:
        if d.get("name") == name and d.get("version") == version:
            return True

    return False


def create_dictionary(lectern_url="http://localhost:3000", dictionary_version="2.1"):
    """
    Creates a dictionary in the Lectern service by POSTing the JSON definition.

    Args:
        lectern_url (str): Base URL for the Lectern service (e.g., http://lectern:3000)
        dictionary_version (str): Version of the dictionary to load.

    Exits:
        The script exits if the POST request fails.
    """
    # Path to JSON resource
    base_dir = Path(__file__).parent  # project root
    dictionary_file = (
        base_dir / "resources" / f"CancerModels_dictionary_{dictionary_version}.json"
    )

    if not dictionary_file.is_file():
        sys.exit(f"❌ Dictionary file not found: {dictionary_file}")

    print(f"📤 Uploading dictionary from: {dictionary_file}")

    # Load JSON
    with dictionary_file.open("r", encoding="utf-8") as f:
        dictionary_data = json.load(f)

    # Lectern API endpoint — adjust path to match actual Lectern dictionary creation endpoint
    endpoint = f"{lectern_url}/dictionaries"

    try:
        response = requests.post(endpoint, json=dictionary_data)
    except requests.RequestException as e:
        sys.exit(f"❌ Failed to connect to Lectern service: {e}")

    if response.status_code not in (200, 201):
        sys.exit(
            f"❌ Failed to create dictionary: {response.status_code} {response.text}"
        )

    print(
        f"✅ Dictionary created successfully in Lectern (status: {response.status_code})"
    )


# def validate_excel_file_original(excel_file_path: Path):
#     """
#     Validates an Excel file by uploading it to the pdcm-lectern-validator service.

#     Args:
#         excel_file_path (Path): Path to the Excel file to validate.
#         validator_url (str): Full URL to the validation endpoint.

#     Returns:
#         dict: Parsed JSON response from the validation service.

#     Exits:
#         If the file does not exist or if the HTTP request fails.
#     """
#     if not excel_file_path.is_file():
#         sys.exit(f"❌ Excel file not found: {excel_file_path}")

#     print(f"📤 Uploading Excel file for validation: {excel_file_path}")

#     with excel_file_path.open("rb") as f:
#         files = {
#             "file": (
#                 excel_file_path.name,
#                 f,
#                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             )
#         }
#         try:
#             response = requests.post(VALIDATOR_URL, files=files)
#             response.raise_for_status()
#         except requests.RequestException as e:
#             sys.exit(f"❌ Validation request failed: {e}")

#     try:
#         json_response = response.json()
#     except ValueError:
#         sys.exit("❌ Failed to parse JSON response from validator.")

#     print(f"✅ Validation response received:")
#     print(json_response)

#     return json_response


def validate_excel_files(excel_files_paths: list[Path]):
    all_files_ok = True
    errors_by_file = {}
    error_report_file_name = "validation_errors.tsv"
    error_report_file_path = Path.cwd() / OUTPUT_DIRECTORY_NAME / error_report_file_name

    # Delete any previous error report file
    if error_report_file_path.exists():
        error_report_file_path.unlink()

    for file in excel_files_paths:
        is_valid, errors = validate_excel_file(file)
        if not is_valid:
            errors_by_file[file] = errors
            all_files_ok = False
    if not all_files_ok:
        report_errors(errors_by_file, error_report_file_path)

    return all_files_ok


def report_errors(errors_by_file: dict[Path, list[dict[str, Any]]], tsv_path: Path):
    """
    Print a report of errors per file and save them to a TSV file.

    Parameters
    ----------
    errors_by_file : dict
        Dictionary mapping file paths (str or Path) to a list of error objects.
    tsv_path : Path
        Path to save the TSV file (default = 'errors_report.tsv').
    """
    if not errors_by_file:
        print("✅ No errors found.")
        return

    # Collect all rows for TSV
    tsv_rows = []

    for file_path, errors in errors_by_file.items():
        print(f"\n📄 File: {file_path}")
        if not errors:
            print("   ✅ No errors in this file.")
            continue

        for i, error in enumerate(errors, start=1):
            error_type = error.get("errorType", "Unknown")
            field_name = error.get("fieldName", "N/A")
            row = error.get("index", "N/A")
            message = error.get("message", "")
            sheet = error.get("sheet", "")

            print(
                f"   {i}. Sheet: {sheet} [{error_type}] Field: {field_name}, Row: {row}"
            )
            if message:
                print(f"      → {message}")

            # Flatten error info for TSV
            row = {
                "file": str(file_path),
                "sheet": sheet,
                "row": row,
                "fieldName": field_name,
                "errorType": error_type,
                "message": message,
            }

            # Merge possible extra 'info' fields directly if needed
            if "info" in error and isinstance(error["info"], dict):
                info_details = []
                for k, v in error["info"].items():
                    info_details.append(f"{k}: {v}")
                    # row[f"info.{k}"] = v
                row["info"] = "\n".join(info_details)

            tsv_rows.append(row)

    # Write TSV report
    if tsv_rows:
        fieldnames = [
            "file",
            "sheet",
            "row",
            "fieldName",
            "errorType",
            "message",
            "info",
        ]

        with tsv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(tsv_rows)

        print(f"\n📝 TSV error report saved to: {tsv_path}")


def validate_excel_file(
    excel_file_path: Path, validator_url="http://localhost:3009/validation/upload-excel"
):
    """
    Validates an Excel file by uploading it to the pdcm-lectern-validator service.

    Args:
        excel_file_path (Path): Path to the Excel file to validate.
        validator_url (str): Full URL to the validation endpoint.

    Returns:
        dict: Parsed JSON response from the validation service.

    Exits:
        If the file does not exist or if the HTTP request fails.
    """
    if not excel_file_path.is_file():
        sys.exit(f"❌ Excel file not found: {excel_file_path}")

    print(f"📤 Uploading Excel file for validation: {excel_file_path}")

    # Determine correct MIME type based on extension
    ext = excel_file_path.suffix.lower()
    if ext == ".xlsx":
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif ext == ".xls":
        mime_type = "application/vnd.ms-excel"
    else:
        sys.exit(
            f"❌ Unsupported file extension '{ext}'. Only .xls and .xlsx are supported."
        )

    with excel_file_path.open("rb") as f:
        files = {"file": (excel_file_path.name, f, mime_type)}
        try:
            response = requests.post(validator_url, files=files)
            response.raise_for_status()
        except requests.RequestException as e:
            # Try to get server's error response content if any
            error_detail = ""
            if e.response is not None:
                try:
                    error_detail = e.response.text
                except Exception:
                    pass
            sys.exit(
                f"❌ Validation request failed: {e}\nServer response: {error_detail}"
            )

    try:
        json_response = response.json()
    except ValueError:
        sys.exit("❌ Failed to parse JSON response from validator.")

    is_valid, errors = process_validation_response(excel_file_path, json_response)
    return is_valid, errors


def process_validation_response(excel_file_path, json_response: str):
    is_valid = False
    errors = []
    status = json_response.get("status", "").lower()
    if status == "valid":
        print("✅ Excel file is VALID according to validator.")
        is_valid = True
    elif status == "invalid":
        print(f"❌ Excel file is {excel_file_path} INVALID. See error details below:\n")
        for sheet in json_response.get("sheetsValidationResults", []):
            if sheet.get("status") == "invalid":
                # print(f"🔹 Sheet: {sheet.get('sheetName')}")
                for err in sheet.get("result", []):
                    err["sheet"] = sheet.get("sheetName")
                    errors.append(err)
    else:
        print(f"⚠️ Unknown validation status: {status}")
    return is_valid, errors
