from threading import Lock
from enum import Enum
from typing import Optional

file_status = {}
file_status_lock = Lock()

class Stage(Enum):
    SAVING = "Saving"
    WAITING = "Waiting for Thread"
    UPLOADING = "Uploading"
    ENCRYPTING = "Encrypting"
    DONE = "Done"
    FAILED = "Failed"

def file_status_set(filename: str, stage: Stage, progress: Optional[int] = None):
    with file_status_lock:
        file_status[filename] = {
            "stage": stage,
            "progress": progress
        }