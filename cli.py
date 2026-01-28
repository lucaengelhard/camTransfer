import itertools
import sys
import os
import time
import argparse
from pathlib import Path

from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.align import Align
from threading import Event

from status import file_status, file_status_lock, Stage
from global_values import FLAGS, FlagType, Mode

stop_event = Event()

def cli(refresh_rate: float = 0.1):
    spinner_cycle = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spinner_index = 0

    with Live(refresh_per_second=1 / refresh_rate, screen=False) as live:
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

def args():
    global FLAGS

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        nargs="?",
        default=Mode.STANDARD,
        type=Mode,
        help=" | ".join([m.value for m in Mode]),
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.cwd(),
        help="Set target directory (defaults to current working directory)",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default="camtransfer.key",
        help="Set path to keyfile (defaults to camtransfer.key)",
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default="camtransfer.priv",
        help="Set path to public key (defaults to camtransfer.pub)",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default="camtransfer.pub",
        help="Set path to private key (defaults to camtransfer.priv)",
    )
    parser.add_argument(
        "--upload-dir",
        type=Path,
        default="/uploads",
        help="Set target directory on the remote",
    )
    parser.add_argument(
        "--unfinished", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--overwrite", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--deletelocal", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument("--upload", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--encrypt", action=argparse.BooleanOptionalAction, default=False
    )

    args = parser.parse_args()

    FLAGS[FlagType.MODE] = args.mode
    FLAGS[FlagType.UPLOAD] = args.upload
    FLAGS[FlagType.ENCRYPT] = args.encrypt
    FLAGS[FlagType.OVERWRITE] = args.overwrite
    FLAGS[FlagType.DELETE_LOCAL] = args.deletelocal and args.upload
    FLAGS[FlagType.HANDLE_UNFINISHED] = args.unfinished

    if not args.dir.is_dir():
        parser.error(f"The path {args.dir} is not a valid directory.")

    save_dir = Path(os.path.join(os.getcwd(), args.dir))
    upload_dir = args.upload_dir
    public_key = None
    private_key = None

    if FLAGS[FlagType.MODE] is Mode.STANDARD and FLAGS[FlagType.ENCRYPT]:
        if args.public_key.exists():
            public_key = encryption.get_key(args.public_key)
        else:
            parser.error(f"No public key at {args.public_key}")

    if FLAGS[FlagType.MODE] is Mode.DECRYPT:
        if args.private_key.exists():
            private_key = encryption.get_key(args.public_key)
        else:
            parser.error(f"No public key at {args.public_key}")

    if FLAGS[FlagType.MODE] is Mode.CREATE_KEYS:
        encryption.create_keys(public=args.public_key, private=args.private_key)

    return save_dir, upload_dir, public_key, private_key
