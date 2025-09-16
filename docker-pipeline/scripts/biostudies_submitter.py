import argparse
import json
import os
import shutil
import requests
from pathlib import Path
from scripts.util import exit_if_dir_not_exists
import scripts.constants as constants

import datetime
import time

from biostudiesclient.api import Api
from biostudiesclient.auth import Auth
import urllib

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# auth = Auth()
# auth.login()
# api = Api(auth)

BASE_URL = "https://wwwdev.ebi.ac.uk/"
# SEARCH_URL = BASE_URL + "biostudies/api/v1/search?query=title%3A{model_id_encoded}"
SEARCH_URL_TEMPLATE = f"{BASE_URL}biostudies/api/v1/CancerModelsOrg/search?query=title%3A{{model_id_encoded}}"

CHECK_IF_EXISTS = False

SKIP_IF_EXISTS = False

skipped = 0


def process_model(data_folder, provider, model):
    print(f"process_model - {data_folder}, {provider}, {model}")

    model_path = os.path.join(data_folder, provider, model)

    model_submission_file = os.path.join(model_path, f"{model}.json")

    if not os.path.exists(model_submission_file):
        raise ValueError(f"No submission file {model_submission_file} found")

    submission = None
    with open(model_submission_file, "r") as file:
        submission = json.load(file)

    file_size = os.path.getsize(model_submission_file)
    if file_size == 0:
        raise ValueError(f"Submission file {model_submission_file} is empty")

    files_folder_name = "molecular_data"
    files_directory = os.path.join(model_path, files_folder_name)

    if os.path.exists(files_directory):
        files = [
            os.path.join(provider, model, files_folder_name, f)
            for f in os.listdir(files_directory)
            if os.path.isfile(os.path.join(files_directory, f))
            and f.__contains__(".tsv")
        ]
        for file in files:
            print("\tUploading", file)
            if " " in file:
                print("There are spaces")
                current_path = os.path.join(data_folder, provider, model)
                new_path = os.path.join("to_fix", provider, model)
                shutil.move(current_path, new_path)
                print("Moved to to_fix location")
                return False

            local_path = os.path.join(data_folder, file)
            # Uploads file to BioStudies
            print("local_path", local_path)
            print("file", file)
            api.upload_file(local_path, file)
        print("Files updated")

    submit(model, submission)
    return True


def get_biostudies_base_url_from_env():
    biostudies_api_url = "https://www.ebi.ac.uk/biostudies/submissions/api"
    return os.environ.get("BIOSTUDIES_API_URL", biostudies_api_url)


def get_password_from_env():
    biostudies_password = "CHANGE_ME"
    return os.environ.get("BIOSTUDIES_TOKEN", biostudies_password)


def requests_retry_session(
    retries=3,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 503, 504),
    session=None,
):
    """
    Returns a requests.Session configured with retry logic.
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"],  # ensure GETs are retried
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def exists_already_old(model_id):
    header = {"X-SESSION-TOKEN": get_password_from_env()}
    model_id_encoded = model_id.replace(" ", "+")
    url = (
        f"{get_biostudies_base_url_from_env()}/submissions?keywords={model_id_encoded}"
    )

    response = requests.get(url, headers=header)
    response.raise_for_status()
    data = response.json()

    accession = None

    if data and data != []:
        # Check they actually match by looking if the title contains the model id
        if f"[{model_id}]" in data[0]["title"]:
            accession = data[0]["accno"]
            print(f"Model {model_id} existed under accession {accession}")

    return accession


def exists_already_old1(model_id):
    header = {"X-SESSION-TOKEN": get_password_from_env()}
    model_id_encoded = model_id.replace(" ", "+")
    url = (
        f"{get_biostudies_base_url_from_env()}/submissions?keywords={model_id_encoded}"
    )

    session = requests_retry_session(retries=5, backoff_factor=2)

    try:
        response = session.get(
            url, headers=header, timeout=10
        )  # timeout is also important
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Error querying {url}: {e}")
        return None

    accession = None
    if data and data != []:
        # Verify by matching the title
        if f"[{model_id}]" in data[0].get("title", ""):
            accession = data["accno"]
            print(f"Model {model_id} existed under accession {accession}")

    return accession


def exists_already(model_id):
    model_id_encoded = model_id.replace(" ", "+")
    url = SEARCH_URL_TEMPLATE.format(model_id_encoded=model_id_encoded)

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    accession = None

    # We might get several results so filtering the exact result is necessary
    hits = data["hits"]
    # print(hits)
    if hits and hits != []:
        # Verify by matching the title
        for element in hits:
            if f"[{model_id}]" in element.get("title", ""):
                accession = element["accession"]
    print("accession>>", accession)
    return accession


def submit(model_id, submission):
    # Does it already exist?
    if CHECK_IF_EXISTS:
        accession = exists_already(model_id)
        if accession:
            submission["accno"] = accession

    response = api.create_submission(submission)

    assert response.json
    assert response.json["accno"]
    print(response.json["accno"])


def main(data_folder):
    processed = 0
    skipped = 0
    if not os.path.exists(data_folder):
        print(f"Directory `{data_folder}` does not exist")
        return

    providers = [
        d
        for d in os.listdir(data_folder)
        if os.path.isdir(os.path.join(data_folder, d))
    ]
    for provider in providers:
        provider_path = os.path.join(data_folder, provider)
        models = [
            m
            for m in os.listdir(provider_path)
            if os.path.isdir(os.path.join(provider_path, m))
        ]
        for model in models:
            if SKIP_IF_EXISTS:
                accession = exists_already(model)
                if accession:
                    skipped += 1
                    print("skipped", skipped)
                    current_path = os.path.join(provider_path, model)
                    new_path = os.path.join("done", provider, model)
                    print("move (dup) from", current_path, "to", new_path)
                    shutil.move(current_path, new_path)
                    continue
            ok = process_model(data_folder, provider, model)
            if ok:
                processed += 1
                if processed % 100 == 0:
                    print("Processed:", processed)
                # Move to done
                current_path = os.path.join(provider_path, model)
                new_path = os.path.join("done", provider, model)
                print("move (sub) from", current_path, "to", new_path)
                shutil.move(current_path, new_path)
    print("Ended")
    print("skipped", skipped)
    print("Processed:", processed)


def get_models_in_path(to_be_submitted_dir: Path):
    models = [
        {
            "model_name": model_path.name,
            "model_path": model_path,
            "provider": model_path.parent.name,
        }
        for provider_dir in Path(to_be_submitted_dir).iterdir()
        if provider_dir.is_dir()
        for model_path in provider_dir.iterdir()
        if model_path.is_dir()
    ]
    return models


def get_formatted_datetime(datetime: datetime):
    return datetime.strftime("%Y-%m-%d %H:%M:%S")


def submit_model(model: dict):
    ok = True
    accno = None
    note = ""
    response = {}
    # datetime.datetime.now()

    model_name = model["model_name"]
    model_path = model["model_path"]
    provider = model["provider"]

    now_formatted = get_formatted_datetime(datetime.datetime.now())
    start = time.time()
    print(f"\nProcessing {provider}/{model_name}. Starting at {now_formatted}")
    existing_accno = exists_already(model["model_name"])
    if existing_accno:
        note = "Already existed"
        accno = existing_accno

    validate_submission_file(model_name, model_path)
    submit_files(model_path, model_name, provider)

    response["valid"] = ok
    response["accno"] = accno
    response["note"] = note
    # This is a combination of 2 dicts
    return model | response


def validate_submission_file(model_name: str, model_path: str):
    if not model_path:
        raise ValueError("Null path for submission file")
    model_submission_file_path = os.path.join(model_path, f"{model_name}.json")

    if not os.path.exists(model_submission_file_path):
        raise ValueError(f"No submission file {model_submission_file_path} found")

    file_size = os.path.getsize(model_submission_file_path)
    if file_size == 0:
        raise ValueError(f"Submission file {model_submission_file_path} is empty")

    return model_submission_file_path


def submit_files(model_path: str, model_name: str, provider: str):
    files_folder_name = "molecular_data"
    files_directory = os.path.join(model_path, files_folder_name)

    if os.path.exists(files_directory):
        files = [
            os.path.join(provider, model_name, files_folder_name, f)
            for f in os.listdir(files_directory)
            if os.path.isfile(os.path.join(files_directory, f))
            and f.__contains__(".tsv")
        ]
        for file in files:
            print("\tUploading", file)
            file_name = file.split(files_folder_name + "/")[1]
            local_path = os.path.join(files_directory, file_name)
            # Uploads file to BioStudies
            # api.upload_file(local_path, file)

        print("Files updated")


def create_report(path: Path, entries: list, headers: list):
    with open(path, "w") as f:
        f.write("\t".join(headers) + "\n")
        for entry in entries:
            values = []
            for header in headers:
                values.append(entry[header])
            f.write("\t".join(values) + "\n")


def submit_all(
    to_be_submitted_dir: Path, submitted_ok_dir: Path, submission_failed: Path
):
    print("\n" + "=" * 40)
    print("🚀 SUBMITTING TO BIOSTUDIES 🚀")
    print("=" * 40 + "\n")

    responses = []

    to_be_submitted_dir.mkdir(parents=True, exist_ok=True)
    submitted_ok_dir.mkdir(parents=True, exist_ok=True)
    submission_failed.mkdir(parents=True, exist_ok=True)

    models_to_submit = get_models_in_path(to_be_submitted_dir)
    print(f"Found {len(models_to_submit)} models to submit")

    for model in models_to_submit:
        responses.append(submit_model(model))

    # Preparing reports

    ok_report_path = to_be_submitted_dir.parent / constants.OK_REPORT
    ok_entries = [entry for entry in responses if entry["valid"]]
    create_report(
        ok_report_path, ok_entries, ["provider", "model_name", "accno", "note"]
    )

    failed_report_path = to_be_submitted_dir.parent / constants.ERROR_REPORT
    failed_entries = [entry for entry in responses if not entry["valid"]]
    create_report(failed_report_path, failed_entries, ["provider", "model_name"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch, process, and formats CancerModels.org data into a structure that fits the BioStudies structurepython."
    )
    parser.add_argument(
        "--data_folder",
        required=True,
        help="Folder where the data to submit is located",
    )

    args = parser.parse_args()

    main(args.data_folder)
