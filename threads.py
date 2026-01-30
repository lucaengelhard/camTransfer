from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from cli import cli

executor = ThreadPoolExecutor(max_workers=4)
spinner_thread = Thread(target=cli, daemon=True)
