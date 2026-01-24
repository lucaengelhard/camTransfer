from cryptography.fernet import Fernet
from pathlib import Path
from typing import Optional
from datetime import datetime

def generate_key(path: Path):
    key = Fernet.generate_key()
    with open(path, "wb") as f:
        f.write(key)

    print(f"Saved key to: {path}")
    return Fernet(key)

def get_key(path: Optional[Path]):
    if path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return generate_key(Path(f"camtransfer_{timestamp}.key"))
    
    with open(path, "rb") as f:
        return Fernet(f.read())

def encrypt(path: Path, fernet: Fernet):
    with open(path, "rb") as f:
        original = f.read()

    encrypted = fernet.encrypt(original)

    with open(path, 'wb') as f:
        f.write(encrypted)

def decrypt(path: Path, fernet: Fernet):
    with open(path, 'rb') as f:
        encrypted = f.read()
    
    decrypted = fernet.decrypt(encrypted)