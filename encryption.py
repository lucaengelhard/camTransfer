from cryptography.fernet import Fernet
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

from pathlib import Path
import os
from enum import Enum

class Suffix(Enum):
    ENC = ".enc"
    DEC = ".dec"

def encrypt(path: Path, public_key: RSA.RsaKey, overwrite: bool = False):
    with open(path, 'rb') as f:
        data = f.read()

    cipher_rsa = PKCS1_OAEP.new(public_key)
    session_key = get_random_bytes(32)
    enc_session_key = cipher_rsa.encrypt(session_key)
    cipher_aes = AES.new(session_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)

    output_path = path.with_name(path.name + Suffix.ENC.value)
    with open(output_path, "wb") as f:
        f.write(enc_session_key)
        f.write(cipher_aes.nonce)
        f.write(tag)
        f.write(ciphertext)

    if overwrite:
        os.remove(path)

def decrypt(path: Path, private_key: RSA.RsaKey, overwrite: bool = False):
    with open(path, "rb") as f:
        enc_session_key = f.read(private_key.size_in_bytes())
        nonce = f.read(16)
        tag = f.read(16)
        ciphertext = f.read()
    
    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(enc_session_key)

    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    data = cipher_aes.decrypt_and_verify(ciphertext, tag)

    if path.suffix == ".enc":
        base = path.with_suffix("")
    else:
        base = path

    output_path = base if overwrite else base.with_suffix(base.suffix + ".dec")

    with open(output_path, "wb") as f:
        f.write(data)

    if overwrite:
        os.remove(path)

def decrypt_dir(path: Path, private_key: RSA.RsaKey, overwrite: bool = False):
    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix == ".enc":
            try:
                decrypt(file_path, private_key, overwrite)
                print(f"Decrypted: {file_path}")
            except Exception as ex:
                print(ex)
                
def get_key(path: Path):
    with open(path, "rb") as keyfile:
        return RSA.import_key(keyfile.read())

def create_keys(public: Path, private: Path):
    print(public)
    if public.exists():
        print(f"Key already exists at {public}")
        return
    
    if private.exists():
        print(f"Key already exists at {private}")
        return

    key = RSA.generate(2048)
    private_key = key.export_key()
    with open(private, "wb") as f:
        f.write(private_key)

    public_key = key.publickey().export_key()
    with open(public, "wb") as f:
        f.write(public_key)

    print(f"Created and saved keys. Public: {public} | Privte: {private}")