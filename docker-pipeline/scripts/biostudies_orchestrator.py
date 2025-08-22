#!/usr/bin/env python3

from pathlib import Path
from datetime import date
import scripts.constants as constants
from scripts.util import exit_if_dir_not_exists
from scripts.biostudies_data_formatter import fetch_and_process_data


def create_submission_files(dir: Path):
    print("Start creation of submission files ...")
    submission_data_dir = dir / constants.SUBMISSION_DATA_DIR
    print("submission_data_dir:", submission_data_dir)
    release_date = str(date.today())
    fetch_and_process_data(submission_data_dir, release_date, skip_processed=False)


def launch_submission(dir: Path):
    print(f"Start submission process. Submission data at {dir.absolute()}")
    exit_if_dir_not_exists(dir)
