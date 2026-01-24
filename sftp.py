from pathlib import Path
import paramiko
import os
from dotenv import load_dotenv
from queue import Queue
from threading import Thread, Event
from collections.abc import Callable
from getpass import getpass
from typing import Optional

sftp = None
transport = None

def get_env():
    load_dotenv()
    HOST = env("SFTP_HOST", prompt="Host")
    USER = env("SFTP_USER", prompt="Username")
    PASSWORD = env("SFTP_PASS", action=getpass, prompt="Password")
    PORT = int(env("SFTP_PORT", prompt="Port", default="22"))

    return HOST, USER, PASSWORD, PORT

def env(key: str, prompt: str, action: Callable[[str], str] = input, default: Optional[str] = None) -> str:
    res = os.getenv(key)
    while res is None or res == "":
        if default is not None:
            res = action(f"{prompt} ({default}): ")
        else:
            res = action(f"{prompt}: ")

        if res == "" and default is not None:
            res = default

    return res

def connect():
    """
    Establish an SFTP connection.
    """
    global sftp, transport

    HOST, USER, PASSWORD, PORT = get_env()

    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USER, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(f"Connected to {HOST} via SFTP.")

def upload(source: Path, remote_path: str):
    """
    Upload a local file to the remote server.
    """
    if sftp is None:
        print("SFTP connection not established.")
        return

    # Upload the file
    print(f"Started upload of {source} to {remote_path}")
    sftp.put(str(source), remote_path)
    print(f"Uploaded {source} to {remote_path}.")
    
def list_remote(path: str = '.'):
    """
    List files in a remote directory.
    """
    if sftp is None:
        print("SFTP connection not established.")
        return
    return sftp.listdir(path)

def close():
    """
    Close the SFTP connection.
    """
    global sftp, transport

    if sftp:
        sftp.close()
        transport.close()
        sftp = None
        transport = None
        print("SFTP connection closed.")
