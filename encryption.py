from cryptography.fernet import Fernet
from pathlib import Path
import os
from enum import Enum

class Suffix(Enum):
    ENC = ".enc"
    DEC = ".dec"

def create_key(path: Path):
    key = Fernet.generate_key()
    with open(path, 'wb') as f:
        f.write(key)
    
    print(f"Created keyfile at {path}")
    
    return Fernet(key)

def encrypt_file(path: Path, fernet: Fernet, overwrite: bool):
    with open(path, 'rb') as f:
        original = f.read()

    encrypted = fernet.encrypt(original)
    target_path = path.with_name(path.name + Suffix.ENC.value)
    with open(target_path, 'wb') as f:
        f.write(encrypted)

    if overwrite:
        os.remove(path)

def decrypt_file(path: Path, fernet: Fernet, overwrite: bool):
    with open(path, 'rb') as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted)

    removed_enc_path = path.with_suffix("") if path.suffix == Suffix.ENC.value else path
    target_path = removed_enc_path if overwrite else removed_enc_path.with_name(removed_enc_path.name + Suffix.DEC.value)
    with open(target_path, 'wb') as f:
        f.write(decrypted)

    if overwrite:
        os.remove(path)

def decrypt_dir(path: Path, fernet: Fernet, overwrite: bool):
    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix == ".enc":
            try:
                decrypt_file(file_path, fernet, overwrite)
                print(f"Decrypted: {file_path}")
            except Exception as ex:
                print(ex)
                continue