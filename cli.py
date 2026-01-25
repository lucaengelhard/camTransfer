import itertools
import sys
import time

from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.align import Align
from threading import Event

from status import file_status, file_status_lock, Stage

real_stdout = sys.__stdout__

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
        real_stdout.write(f"\r\033[K{spin_char} {status_line}")
        real_stdout.flush()
        time.sleep(0.1)


stop_event = Event()

def cli(refresh_rate: float = 0.1):
    spinner_cycle = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    spinner_index = 0

    with Live(refresh_per_second=1/refresh_rate, screen=False) as live:
        while not stop_event.is_set():
            table = Table(expand=True)
            table.add_column("File", no_wrap=True)
            table.add_column("Stage", no_wrap=True)
            table.add_column("Progress", justify="right", no_wrap=True)

            with file_status_lock:
                active_files = [
                    (fname, info.get("stage"), info.get("progress", 0))
                    for fname, info in file_status.items()
                    if info.get("stage") not in (Stage.DONE, Stage.FAILED)
                ]

            if active_files:
                for fname, stage, progress in active_files:
                    stage_text = stage.value if stage else "?"
                    progress_text = f"{progress}%" if progress is not None else ""
                    table.add_row(fname, stage_text, progress_text)
            else:
                table.add_row("Waiting for image...", "", "")

            spin_char = spinner_cycle[spinner_index % len(spinner_cycle)]
            spinner_index += 1

            live.update(Align.left(f"{spin_char} "))
            live.update(table)

            time.sleep(refresh_rate)