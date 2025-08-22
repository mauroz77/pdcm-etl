#!/usr/bin/env python3
"""
docker-pipeline.py

Orchestrator for the Cancer Models to BioStudies pipeline.

This script:
1. Accepts a metadata provider name as input.
2. Runs a Docker-based processing pipeline for cancer model metadata from the given provider.
3. Submits processed metadata to BioStudies.

Example usage:
    python docker-pipeline.py -p provider_name
"""

import argparse
import sys
from pathlib import Path
import re
from scripts.excel_validator import init_validator, validate_excel_files
from scripts.biostudies_orchestrator import create_submission_files, launch_submission
from scripts import xlsx_to_tsv
from scripts.etl_orchestrator import launch_etl
import scripts.constants as constants
import shutil

# import scripts.etl_orchestrator
from scripts.util import (
    copy_file_with_dirs,
)


def validate_provider(provider: str):
    """
    Validates that the provider string contains only letters (A–Z, a–z), hyphen (-) or underscore (_).

    Rules:
    - Must not be empty.
    - Must contain only letters (no numbers, spaces, or special characters).

    Args:
        provider (str): Provider abbreviation to validate.

    Exits:
        The script exits with an error message if validation fails.
    """
    # Must not be empty or whitespace
    if not provider.strip():
        sys.exit("❌ Invalid provider: cannot be empty.")

    # Must contain only letters
    if not re.match(r"^[-_A-Za-z]+$", provider):
        sys.exit("❌ Invalid provider: only letters (A–Z, a–z) are allowed.")

    print(f"✅ Provider '{provider}' is valid.")


def get_input_files_dir(provider: str):
    base_dir = Path(__file__).parent
    return base_dir / constants.INPUT_DIR / provider


def find_input_files(provider: str):
    """
    Checks whether the expected input data folder exists for a given provider,
    and whether it contains at least one Excel file starting with the provider name
    followed by an underscore.

    Example of valid file: VHIO-BC_metadata.xlsx

    Args:
        provider (str): The provider name (used as subdirectory).

    Exits:
        The script will exit with an error message if the folder is missing
        or no valid Excel file is found.
    """
    # base_dir = Path(__file__).parent
    input_folder_path = get_input_files_dir(provider)

    print(f"Checking input folder: {input_folder_path}")

    if input_folder_path.is_dir():
        print("✅ Input folder exists.")
    else:
        sys.exit(
            f"❌ Missing required folder: {input_folder_path}\n"
            "This folder must contain the Excel template to be processed."
        )

    # Check that at least an Excel file exists. All Excel files MUST start witht the provider abbreviation
    excel_files: list[Path] = list(input_folder_path.glob(f"{provider}_*.xls")) + list(
        input_folder_path.glob(f"{provider}_*.xlsx")
    )

    if not excel_files:
        sys.exit(
            f"❌ No valid Excel files found in '{input_folder_path}'.\n"
            f"Expected at least one file starting with '{provider}_' "
            f"and ending with .xls or .xlsx."
        )

    print(f"✅ Found {len(excel_files)} matching Excel file(s):")
    for file in excel_files:
        print(f"   - {file.name}")
    return excel_files


def validate_input_files(excel_files: list[Path]):
    # Initialise the docker containers needed for the validation process
    init_validator()
    # Validate all the Excel files
    ok = validate_excel_files(excel_files)
    if not ok:
        sys.exit(
            "❌ Some Excel files had data errors. Check the report, fix the issues and try again."
        )


def convert_excel_files_to_tsv(excel_files: list[Path], provider: str):
    print("Converting to tsv")
    # Create a copy of the input files to the output folder
    for file in excel_files:
        original_path = str(file.absolute())
        split = original_path.split(constants.INPUT_DIR)
        new_path = (
            f"{split[0]}{constants.OUTPUT_DIR}/{constants.TEMPLATES_DIR}{split[1]}"
        )
        copy_file_with_dirs(original_path, new_path)
        dir_to_process = Path(new_path).parent
        xlsx_to_tsv.main(["-d", str(dir_to_process.absolute()), "-a"])


# def generate_submission_files(biostudies_path: Path):
#     print("Generating submission files")
#     biostudies_path = Path(__file__).parent / constants.OUTPUT_DIR / constants.BIOSTUDIES_DIR
#     create_submission_files(biostudies_path)


def get_biostudies_submission_dir_path():
    return Path(__file__).parent / constants.OUTPUT_DIR / constants.BIOSTUDIES_DIR


def handle_biostudies_submission(only_generate_files: bool):
    biostudies_path = (
        Path(__file__).parent / constants.OUTPUT_DIR / constants.BIOSTUDIES_DIR
    )
    create_submission_files(biostudies_path)


def setup_args():
    parser = argparse.ArgumentParser(
        description="Run the Docker pipeline to process and submit cancer model metadata to BioStudies."
    )
    parser.add_argument(
        "-p",
        "--provider",
        required=True,
        help="Provider name (e.g., 'PDCM', 'JAX'). Make sure an entry for this provider exists in etl-assets/providers.csv.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        help="Generate the submission files for BioStudies without actually submitting them.",
        action="store_true",
    )

    parser.add_argument(
        "-s",
        "--submit-only",
        help="Submit the metadata to BioStudies without generating any data. Use this flag if the data has already been processed and only submission is required.",
        action="store_true",
    )
    parser.add_argument(
        "-k",
        "--keep-etl-folders",
        help="Prevent deletion of ETL output folders before rerunning the process.",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = setup_args()

    print("Starting Cancer Models to BioStudies pipeline (Docker version)...")

    biostudies_dir_path = get_biostudies_submission_dir_path()

    submission_data_dir_path = biostudies_dir_path / constants.SUBMISSION_DATA_DIR

    if args.submit_only:
        print(
            f"Running the pipeline with the --submit-only flag. No data will be generated, so the system expects data at {submission_data_dir_path} to already exist."
        )
        launch_submission(submission_data_dir_path)
    else:
        create_initial_folders(args.keep_etl_folders)

        provider = args.provider

        validate_provider(provider)
        provider = provider.upper()
        input_files = find_input_files(provider)

        validate_input_files(input_files)

        convert_excel_files_to_tsv(input_files, provider)

        print("Ready to continue with ETL stage")

        launch_etl(provider)

        print("Ready to create BioStudies submission files ...")
        create_submission_files(biostudies_dir_path)

        if not args.dry_run:
            launch_submission(submission_data_dir_path)

    print("✅ Pipeline finished.")


def create_initial_folders(keep_etl_folders: bool):
    # Path to the "data" folder inside the current working directory
    data_folder = Path.cwd() / constants.OUTPUT_DIR

    # Create the folder (and any missing parents if needed)
    data_folder.mkdir(parents=True, exist_ok=True)

    etl_input_path = data_folder / constants.HOST_ETL_INPUT_DIR
    etl_output_path = data_folder / constants.HOST_ETL_OUTPUT_DIR

    if keep_etl_folders:
        print("ETL folders not deleted")
    else:
        print("Deleting any existing ETL folders")
        if etl_input_path.exists() and etl_input_path.is_dir():
            shutil.rmtree(etl_input_path)
        if etl_output_path.exists() and etl_output_path.is_dir():
            shutil.rmtree(etl_output_path)

    etl_input_path.mkdir(parents=True, exist_ok=True)
    etl_output_path.mkdir(parents=True, exist_ok=True)

    # Path to the "config" folder
    config_folder = Path.cwd() / constants.CONFIG_DIR
    config_folder.mkdir(parents=True, exist_ok=True)

    # create ETL_OUTPUT_DIRECTORY
    etl_output_folder = (
        Path.cwd() / constants.OUTPUT_DIR / constants.HOST_ETL_OUTPUT_DIR
    )
    etl_output_folder.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
