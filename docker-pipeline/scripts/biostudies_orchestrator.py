#!/usr/bin/env python3

from pathlib import Path
from datetime import date
import os
import sys
import scripts.constants as constants
from scripts.util import exit_if_dir_not_exists, dir_content_copy
from scripts.biostudies_data_formatter import fetch_and_process_data
from scripts.biostudies_submitter import submit_all


def create_submission_files(dir: Path):
    print("Start creation of submission files ...")
    submission_data_dir = dir / constants.SUBMISSION_DATA_DIR
    print("submission_data_dir:", submission_data_dir)
    release_date = str(date.today())
    fetch_and_process_data(submission_data_dir, release_date, skip_processed=False)


def launch_submission(dir: Path):
    print(f"Start submission process. Submission data at {dir.absolute()}")
    exit_if_dir_not_exists(dir)
    copy_submission_data_to_processing_dir(dir)
    # Define the paths
    biostudies_dir = dir.parent
    to_be_submitted_dir = biostudies_dir / constants.TO_BE_SUBMITTED_DIR
    print("to_be_submitted_dir", to_be_submitted_dir)
    submitted_ok_dir = biostudies_dir / constants.SUBMITTED_OK_DIR
    print("submitted_ok_dir", submitted_ok_dir)
    submission_failed = biostudies_dir / constants.SUBMISSIONS_FAILED_DIR
    print("submission_failed", submission_failed)
    # check_env_vars_exist()
    submit_all(to_be_submitted_dir, submitted_ok_dir, submission_failed)

    # ...
    # Here we need to call logic to submission...
    # ... How to implement retry?
    # ... Create a report: model_id vs accession id


def copy_submission_data_to_processing_dir(submission_dir: Path):
    to_be_submitted = submission_dir.parent / constants.TO_BE_SUBMITTED_DIR
    dir_content_copy(submission_dir, to_be_submitted, verbose=False)


def check_env_vars_exist():
    if not os.environ.get(constants.BIOSTUDIES_USERNAME):
        sys.exit(f"❌ Env var {constants.BIOSTUDIES_USERNAME} does not exist.")
    if not os.environ.get(constants.BIOSTUDIES_PASSWORD):
        sys.exit(f"❌ Env var {constants.BIOSTUDIES_PASSWORD} does not exist.")
    print("Env vars in place")
