from pathlib import Path
from datetime import datetime


def crate_date_dir(root: Path, time=datetime.now()) -> Path:
    return (
        root
        / Path(str(time.year))
        / Path(f"{time.year}_{str(time.month).zfill(2)}_{str(time.day).zfill(2)}")
    )
