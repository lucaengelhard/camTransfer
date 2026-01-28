from pathlib import Path
from typing import Tuple


def get_sidecar_file_path(path: Path):
    file_path = path.with_name(path.name + ".lock")
    return file_path

def create_sidecar_file(path: Path):
    sidecar_path = get_sidecar_file_path(path)
    if sidecar_path.exists():
        return sidecar_path
    
    with open(sidecar_path, "w") as f:
        f.write(path.name)

    return sidecar_path

def write_sidecar(path: Path, data: Tuple[str, str]):
    sidecar_path = get_sidecar_file_path(path)
    
    current_data = {}
    if sidecar_path.exists():
        current_data = get_key_value(sidecar_path)

    current_data[data[0]] = data[1]

    write_key_value(sidecar_path, current_data)

def read_sidecar(path) -> dict:
    return get_key_value(get_sidecar_file_path(path))

def get_key_value(path: Path, separator: str = "=") -> dict:
    result = {}
    with open(path, "rt") as f:
        for line in f:
            key, value = line.partition(separator)[::2]
            result[key.strip()] = value.strip()

    return result

def write_key_value(path: Path, data: dict, separator: str = "="):
    with open(path, "w") as f:
        for key, value in data.items():
            f.write(f"{key}{separator}{value}\n")
