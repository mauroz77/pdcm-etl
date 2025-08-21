#!/usr/bin/env python3

from pathlib import Path
import scripts.constants as constants
from scripts.util import exit_if_dir_not_exists


def create_submission_files(dir: Path):
    print("Start creation of submission files ...")
    submission_data_dir = dir / constants.SUBMISSION_DATA_DIR
    print("submission_data_dir:", submission_data_dir)


def launch_submission(dir: Path):
    print(f"Start submission process. Submission data at {dir.absolute()}")
    exit_if_dir_not_exists(dir)
