from dotenv import load_dotenv
from collections.abc import Callable
from getpass import getpass
from typing import Optional
import os

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