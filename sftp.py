from pathlib import Path
import paramiko
import os

from status import file_status, file_status_lock, file_status_set, Stage
from env import get_env


HOST, USER, PASSWORD, PORT = get_env()

def test_connection():
    global HOST, USER, PASSWORD, PORT

    print(f"Testing SFTP connection to {HOST}:{PORT}...")

    transport = paramiko.Transport((HOST, PORT))
    try:
        transport.connect(username=USER, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.listdir(".")
        print("SFTP connection OK.")
        return True
    finally:
        sftp.close()
    
    transport.close()

def upload(source: Path, remote_path: str):
    global HOST, USER, PASSWORD, PORT
    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USER, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)

    def progress_callback(transferred, total):
        file_status_set(source.name, Stage.UPLOADING, int(transferred / total * 100))

    try:
        sftp.put(str(source), remote_path, callback=progress_callback)
        file_status_set(source.name, Stage.UPLOADING, 100)
    except Exception as e:
        pass
    finally:
        sftp.close()
        transport.close()