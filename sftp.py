from pathlib import Path
import paramiko
import os
from dotenv import load_dotenv

sftp = None
transport = None

def get_env():
    load_dotenv()
    HOST = os.getenv("SFTP_HOST")
    USER = os.getenv("SFTP_USER")
    PASSWORD = os.getenv("SFTP_PASS")
    PORT = int(os.getenv("SFTP_PORT", 22))

    return HOST, USER, PASSWORD, PORT

def connect():
    """
    Establish an SFTP connection.
    """

    HOST, USER, PASSWORD, PORT = get_env()

    global sftp, transport
    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USER, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(f"Connected to {HOST} via SFTP.")

# TODO: create queue, so that upload isn't blocking
def upload(source: Path, remote_path: str):
    """
    Upload a local file to the remote server.
    """
    if sftp is None:
        print("SFTP connection not established.")
        return

    # List files in remote directory
    print("Remote directory before upload:", sftp.listdir('.'))

    # Upload the file
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
