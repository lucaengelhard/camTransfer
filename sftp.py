from pathlib import Path
import paramiko
import os
from dotenv import load_dotenv
from queue import Queue
from threading import Thread, Event

sftp = None
transport = None

upload_thread = None
upload_queue = Queue()
stop_event = Event()

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
    global sftp, transport, upload_thread

    HOST, USER, PASSWORD, PORT = get_env()

    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USER, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(f"Connected to {HOST} via SFTP.")

    upload_thread = Thread(target=_upload_worker, daemon=True)
    upload_thread.start()

def upload(source: Path, remote_path: str):
    """
    Non-blocking: add upload job to queue.
    """
    if sftp is None:
        print("SFTP connection not established.")
        return

    upload_queue.put((source, remote_path))
    print(f"Queued {source} -> {remote_path}")

    """
    Upload a local file to the remote server.
    
    if sftp is None:
        print("SFTP connection not established.")
        return

    # List files in remote directory
    print("Remote directory before upload:", sftp.listdir('.'))

    # Upload the file
    sftp.put(str(source), remote_path)
    print(f"Uploaded {source} to {remote_path}.") """

def _upload_worker():
    """
    Background thread that processes upload queue.
    """
    while not stop_event.is_set():
        try:
            source, remote_path = upload_queue.get(timeout=1)
        except:
            continue

        try:
            print(f"Uploading {source}...")
            sftp.put(str(source), remote_path)
            print(f"Uploaded {source} -> {remote_path}")
            print(f"Queue length: {upload_queue.qsize()}")
        except Exception as e:
            print(f"Upload failed for {source}: {e}")
        finally:
            upload_queue.task_done()
    


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

    stop_event.set()

    if worker_thread:
        worker_thread.join()

    if sftp:
        sftp.close()
        transport.close()
        sftp = None
        transport = None
        print("SFTP connection closed.")
