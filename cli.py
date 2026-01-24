import itertools
import sys
import time

from status import file_status, file_status_lock, Stage

def display_spinner():
    spinner_cycle = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
    while True:
        spin_char = next(spinner_cycle)
        with file_status_lock:
            statuses = []
            for fname, info in file_status.items():
                stage = info.get("stage")
                progress = info.get("progress", 0)
                if stage is not Stage.DONE and stage is not Stage.FAILED:
                    if progress is None:
                        statuses.append(f"{fname}: {stage.value}")
                    else:
                        statuses.append(f"{fname}: {stage.value} {progress}%")

        status_line = " | ".join(statuses) if statuses else "Waiting for image..."
        sys.stdout.write(f"\r\033[K{spin_char} {status_line}")
        sys.stdout.flush()
        time.sleep(0.1)
