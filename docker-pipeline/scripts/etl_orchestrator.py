#!/usr/bin/env python3

from pathlib import Path
from scripts.util import (
    wait_for_container_health,
    remove_compose_service,
    dir_content_copy,
    wait_for_service,
)
import subprocess
import sys
import re
import csv
import docker
import time
import requests
import psycopg2

import scripts.constants as constants

CONFIG_DIRECTORY = "config"

LUIGI_TEMPLATE_NAME = "luigi_template.cfg"
LUIGI_FILE_NAME = "luigi.cfg"

# Database configuration
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "pdcm"
DB_USER = "pdcm_admin"
DB_PASSWORD = "pdcm_admin"

# Input/Output paths
DATA_DIR = "/app/data/input"
DATA_DIR_OUT = "/app/data/output"

# Spark related
SPARK_DRIVER_MEMORY = "4g"
SPARK_EXECUTOR_MEMORY = "4g"
ETL_ENV = "local"
ETL_DEPLOY_MODE = "local"
SPARK_LOCAL_DIR = "spark.local.dir=/tmp"

ETL_ASSETS_DIR = Path(__file__).parent.parent / "etl-assets"


def create_luigi_conf_file(provider: str):
    print("Creating a luigi configuration file for running the ETL ...")
    template_path = Path(__file__).parent.parent.parent / LUIGI_TEMPLATE_NAME
    if not template_path.exists():
        sys.exit(
            f"❌ Could not find the Luigi template file. Expected at {template_path}"
        )

    # Read the full config file
    with open(template_path, "r") as f:
        config_text = f.read()

    config_text = config_text.replace("DATA_DIR", DATA_DIR, 1)
    config_text = config_text.replace("DATA_DIR_OUT", DATA_DIR_OUT, 1)
    config_text = config_text.replace("ETL_ENVIRONMENT", ETL_ENV)

    config_text = config_text.replace("DB_HOST", DB_HOST)
    config_text = config_text.replace("DB_PORT", DB_PORT)
    config_text = config_text.replace("DB_HOST", DB_HOST)
    config_text = config_text.replace("DB_NAME", DB_NAME)
    config_text = config_text.replace("DB_USER", DB_USER)
    config_text = config_text.replace("DB_PASSWORD", DB_PASSWORD)

    config_text = config_text.replace("SPARK_DRIVER_MEMORY", SPARK_DRIVER_MEMORY)
    config_text = config_text.replace("SPARK_EXECUTOR_MEMORY", SPARK_EXECUTOR_MEMORY)
    config_text = config_text.replace("SPARK_LOCAL_DIR", SPARK_LOCAL_DIR)

    providers_list = [p.strip() for p in provider.split(",") if p.strip()]

    new_providers_str = (
        "providers=[" + ", ".join(f'"{p}"' for p in providers_list) + "]"
    )

    # Pattern to match root-level providers line + any indented continuation lines
    # ^providers=.*       → line starting with 'providers='
    # (?:\n[ \t]+.*)*     → zero or more continuation lines starting with whitespace
    pattern = re.compile(r"(?m)^providers=.*(?:\n[ \t]+.*)*")

    # Replace with new value
    config_text, count = pattern.subn(new_providers_str, config_text)

    # Remove values that are only needed in a cluster
    lines = config_text.split("\n")
    init_cluster_conf = 0
    end_cluster_conf = 0

    for i, line in enumerate(lines):
        if "#INIT_CLUSTER_SECTION" in line:
            init_cluster_conf = i
        elif "#END_CLUSTER_SECTION" in line:
            end_cluster_conf = i

    lines = lines[0 : init_cluster_conf + 1] + lines[end_cluster_conf:]
    config_text = "\n".join(lines)

    local_config_file_path = Path.cwd() / CONFIG_DIRECTORY / LUIGI_FILE_NAME
    with open(local_config_file_path, "w") as f:
        f.write(config_text)
    print(f"Luigi configuration file created: {local_config_file_path}")


def copy_etl_assets_to_etl_input_dir():
    """
    Copy the etl-assets folder content to the input folder in the ETL, which will be visible from the etl
    container.
    These files are required for the ETL process: mapping rules, ontology data, etc.
    """
    # etl_assets_dir = Path(__file__).parent.parent / "etl-assets"
    new_location = (
        Path(__file__).parent.parent
        / constants.OUTPUT_DIR
        / constants.HOST_ETL_INPUT_DIR
    )
    dir_content_copy(ETL_ASSETS_DIR, new_location)


def ensure_ncit_obo(
    filename="ncit.obo",
    url="http://purl.obolibrary.org/obo/ncit.obo",
):
    """
    Ensure ncit.obo exists in asset_dir. If not, download from url.

    Parameters:
    - asset_dir: Path-like object for assets directory
    - filename: Name of the .obo file
    - url: URL to download .obo file

    Returns:
    - Path to the ncit.obo file
    """
    ontology_dir = ETL_ASSETS_DIR / "ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)

    file_path = ontology_dir / filename
    print(f"At ensure_ncit_obo {file_path} ...")

    if not file_path.is_file():
        print(f"Downloading {filename} from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with file_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"{filename} downloaded to {file_path}.")
    else:
        print(f"{filename} already exists at {file_path}.")

    return file_path


def get_provider_data(provider: str):
    print("Getting provider data:", provider)
    providers_file_path = Path(__file__).parent.parent / "etl-assets" / "providers.csv"
    print(providers_file_path)
    if providers_file_path.exists():
        print("FIle ok")


def find_provider_info(provider_abbreviation: str) -> dict:
    """
    Reads the CSV at csv_filepath and searches for a row where 'abbreviation' matches provider_abbreviation.
    Returns the row as a dictionary if found.
    Raises ValueError if no matching row is found.
    """
    csv_filepath = Path(__file__).parent.parent / "etl-assets" / "providers.csv"
    with open(csv_filepath, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["abbreviation"] == provider_abbreviation:
                return row
    raise ValueError(f"Provider '{provider_abbreviation}' not found in {csv_filepath}")


def create_provider_yaml_file(provider: str):
    print("calling create_provider_yaml_file", provider)
    # Name of the yaml file to create
    yaml_file_name = f"{provider}_source.yaml"
    # The ETL expects a web dir under the provider dir
    web_dir = (
        Path(__file__).parent.parent
        / constants.OUTPUT_DIR
        / constants.TEMPLATES_DIR
        / provider
        / "web"
    )
    # Path where the ETL expects the yaml file
    yaml_path = web_dir / yaml_file_name
    print("yaml_path", yaml_path)

    # Path where the template can be found
    template_path = (
        Path(__file__).parent.parent / "scripts" / "resources" / "source_template.yaml"
    )
    print("template_path", template_path)

    # Read the full config file
    with open(template_path, "r") as f:
        config_text = f.read()

    provider_data = find_provider_info(provider)

    project_name = provider_data.get("project_name", "")
    provider_name = provider_data.get("name", "")
    provider_type = provider_data.get("provider_type", "")
    view_at = provider_data.get("view_data_at", provider)

    config_text = config_text.replace("[PROJECT]", project_name)
    config_text = config_text.replace("[PROVIDER_ABBREVIATION]", provider)
    config_text = config_text.replace("[PROVIDER_NAME]", provider_name)
    config_text = config_text.replace("[PROVIDER_TYPE]", provider_type)
    config_text = config_text.replace("[VIEW_AT]", view_at)

    web_dir.mkdir(parents=True, exist_ok=True)

    with open(yaml_path, "w") as f:
        f.write(config_text)
    print(f"Provider yaml file created at: {yaml_path}")


def grant_select_to_web_anon(
    host="localhost",  # If Docker exposes Postgres on localhost
    port=5438,  # Host port mapped in docker-compose ("5438:5432")
    database="pdcm",
    user="pdcm_admin",
    password="pdcm_admin",
    schema="pdcm_api",
    role="web_anon",
):
    conn = psycopg2.connect(
        host=host, port=port, dbname=database, user=user, password=password
    )
    conn.autocommit = True
    cur = conn.cursor()
    sql = f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema}" TO {role};'
    cur.execute(sql)
    print(f"Granted SELECT on all tables in schema '{schema}' to role '{role}'.")
    cur.close()
    conn.close()


def init_containers():
    """
    Starts a postgres DB, luigi scheduler and pdcm-etl containers, and starts the execution of the ETL
    """
    compose_dir = Path(__file__).parent.parent.parent

    run_compose_service("db", compose_dir)
    wait_for_container_health("pdcm-etl-db-1")

    remove_compose_service("luigi-scheduler", compose_dir)
    run_compose_service("luigi-scheduler", compose_dir)
    wait_for_container_health("pdcm-etl-luigi-scheduler-1")

    remove_compose_service("luigi-worker", compose_dir)
    run_compose_service("luigi-worker", compose_dir)

    # Wait for the luigi-worker container to stop before reading logs
    wait_for_container_to_exit("pdcm-etl-luigi-worker-1")

    # Now safe to check logs
    check_luigi_worker_logs("pdcm-etl-luigi-worker-1")

    # This is require to allow PostREST to have permission to expose the schema
    grant_select_to_web_anon()

    # Init PostREST container to expose data through REST API
    run_compose_service("postgrest", compose_dir)
    # wait_for_container_health("pdcm-etl-postgrest-1")
    API_URL = "http://localhost:4000"
    wait_for_service(API_URL)


def wait_for_container_to_exit(
    container_name, poll_interval=60, dot_interval=5, timeout=None
):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        print(f"Container '{container_name}' not found.")
        return None

    print("Processing ", end="", flush=True)

    start_time = time.time()
    while container.status == "running":
        elapsed = 0
        while elapsed < poll_interval:
            print(".", end="", flush=True)
            time.sleep(dot_interval)
            elapsed += dot_interval

            if timeout and (time.time() - start_time) > timeout:
                print("\nTimeout reached, stopping wait.")
                return container

        container.reload()

    print("\nFinished processing")
    return container


def run_compose_service(service_name, compose_dir):
    print(f"🚀 Starting {service_name} from {compose_dir} ...")
    try:
        subprocess.run(
            ["docker-compose", "up", "-d", "--force-recreate", service_name],
            cwd=compose_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ Failed to start {service_name}: {e}")


def check_luigi_worker_logs(container_name="pdcm-etl-luigi-worker-1"):
    """
    Checks the logs of the specified luigi-worker container.
    Raises RuntimeError if failure indications are found in the logs.
    """
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        raise RuntimeError(f"Container '{container_name}' not found.")

    logs = container.logs(stream=True)
    errors = []

    for log in logs:
        log_entry = log.decode("utf-8")
        if (
            "Exception" in log_entry
            or "failed:" in log_entry
            or "progress looks :(" in log_entry
        ):
            errors.append(log_entry)

    if errors != []:
        errors_string = "".join(errors)
        print("❌ Pipeline failed. The ETL found issues while processing the files:")
        sys.exit(errors_string)
    else:
        print("✅ ETL finished without errors.")


def launch_etl(provider: str):
    print("ETL orchestrator")
    create_luigi_conf_file(provider)
    ensure_ncit_obo()
    copy_etl_assets_to_etl_input_dir()
    create_provider_yaml_file(provider)
    init_containers()
