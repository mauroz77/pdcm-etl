#!/usr/bin/env python3

import time
import requests
import sys
import shutil
import subprocess

from pathlib import Path


def wait_for_service(url: str, timeout: int = 120, interval: int = 5):
    """
    Waits until the HTTP service at `url` responds with status code 200 or timeout is reached.
    """
    print(f"⏳ Waiting for service at {url} to be ready...")
    start_time = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ Service at {url} is ready.")
                return
        except requests.RequestException:
            pass
        if time.time() - start_time > timeout:
            sys.exit(f"❌ Timed out waiting for service at {url}")
        time.sleep(interval)


def wait_for_container_health(container_name, timeout=60):
    for _ in range(timeout):
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "healthy":
            print(f"{container_name} is healthy")
            return True
        time.sleep(1)
    sys.exit(f"❌ {container_name} didn't become healthy in time")


def copy_file_with_dirs(src_path, dest_path):
    """
    Copies a file from src_path to dest_path.
    Creates any missing destination directories.

    Parameters:
        src_path (str | Path): Path to the source file
        dest_path (str | Path): Path to the destination file
    """
    src = Path(src_path)
    dest = Path(dest_path)

    if not src.exists():
        raise FileNotFoundError(f"Source file does not exist: {src}")

    # Create destination directories if they don't exist
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy file (with metadata like modified time)
    shutil.copy2(src, dest)

    print(f"✅ Copied {src} → {dest}")


def dir_content_copy(source_dir, destination_dir):
    """
    Copy all contents of source directory to destination directory,
    mimicking Docker COPY behavior.

    Args:
        source_dir (str): Source directory path
        destination_dir (str): Destination directory path

    Features:
    - Copies directory contents (not the directory itself)
    - Merges with existing files/directories (doesn't delete existing)
    - Only copies visible files (skips hidden files starting with '.')
    - Creates destination directory if it doesn't exist
    """
    source_path = Path(source_dir)
    dest_path = Path(destination_dir)

    print("FROM", source_path)
    print("TO", destination_dir)

    # Check if source directory exists
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(
            f"Source directory '{source_dir}' does not exist or is not a directory"
        )

    # Create destination directory if it doesn't exist
    dest_path.mkdir(parents=True, exist_ok=True)

    # Copy all visible contents from source to destination
    for item in source_path.iterdir():
        # Skip hidden files and directories (starting with '.')
        if item.name.startswith("."):
            continue

        dest_item = dest_path / item.name

        if item.is_file():
            # Copy file, overwriting if it exists
            shutil.copy2(item, dest_item)
            print(f"Copied file: {item} -> {dest_item}")
        elif item.is_dir():
            # Recursively copy directory contents
            if dest_item.exists():
                # Directory exists, merge contents
                dir_content_copy(str(item), str(dest_item))
            else:
                # Directory doesn't exist, copy entire directory
                shutil.copytree(item, dest_item)
                print(f"Copied directory: {item} -> {dest_item}")


def remove_compose_service(service_name, compose_dir):
    print(f"🧹 Ensuring {service_name} is fresh ...")
    try:
        subprocess.run(
            ["docker-compose", "rm", "-sf", service_name],
            cwd=compose_dir,
            check=True,
        )
        print(f"🧹 Removed old {service_name} container.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Could not remove {service_name} (might not exist): {e}")
