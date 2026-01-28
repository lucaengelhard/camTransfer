import gphoto2 as gp
import time
import os
import sys
import argparse
from pathlib import Path
from Crypto.PublicKey import RSA
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
import itertools
import sys
import time

# Local modules
from camera import connect_camera, get_camera_name
import sftp
import encryption
import cli
from status import file_status, file_status_lock, file_status_set, Stage
from sidecar import (
    create_sidecar_file,
    get_sidecar_file_path,
    get_key_value,
    write_sidecar,
)

# Globals
FLAG_UPLOAD = None
FLAG_ENCRYPT = None
FLAG_MODE = None
FLAG_OVERWRITE = None
FLAG_DELETE_LOCAL = None
FLAG_HANDLE_UNFINISHED = None


class Mode(Enum):
    STANDARD = "standard"
    DECRYPT = "decrypt"
    CREATE_KEYS = "create-keys"


executor = ThreadPoolExecutor(max_workers=4)
spinner_thread = Thread(target=cli.cli, daemon=True)


def main():
    global FLAG_UPLOAD, FLAG_MODE, FLAG_OVERWRITE, FLAG_HANDLE_UNFINISHED

    save_dir, upload_dir, public_key, private_key = args()

    if FLAG_MODE is Mode.CREATE_KEYS:
        return 0

    if FLAG_MODE is Mode.DECRYPT:
        encryption.decrypt_dir(save_dir, private_key, FLAG_OVERWRITE)
        return 0

    if FLAG_UPLOAD:
        sftp.test_connection()

    if FLAG_HANDLE_UNFINISHED:
        handle_unfinished(save_dir, upload_dir, public_key)

    camera = connect_camera()
    poll_image(
        timeout=3000,
        camera=camera,
        save_dir=save_dir,
        public_key=public_key,
        upload_dir=upload_dir,
    )

    return 0


def args():
    global FLAG_UPLOAD, FLAG_ENCRYPT, FLAG_MODE, FLAG_OVERWRITE, FLAG_DELETE_LOCAL, FLAG_HANDLE_UNFINISHED

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

    FLAG_MODE = args.mode
    FLAG_UPLOAD = args.upload
    FLAG_ENCRYPT = args.encrypt
    FLAG_OVERWRITE = args.overwrite
    FLAG_DELETE_LOCAL = args.deletelocal and args.upload
    FLAG_HANDLE_UNFINISHED = args.unfinished

    if not args.dir.is_dir():
        parser.error(f"The path {args.dir} is not a valid directory.")

    save_dir = Path(os.path.join(os.getcwd(), args.dir))
    upload_dir = args.upload_dir
    public_key = None
    private_key = None

    if FLAG_MODE is Mode.STANDARD and FLAG_ENCRYPT:
        if args.public_key.exists():
            public_key = encryption.get_key(args.public_key)
        else:
            parser.error(f"No public key at {args.public_key}")

    if FLAG_MODE is Mode.DECRYPT:
        if args.private_key.exists():
            private_key = encryption.get_key(args.public_key)
        else:
            parser.error(f"No public key at {args.public_key}")

    if FLAG_MODE is Mode.CREATE_KEYS:
        encryption.create_keys(public=args.public_key, private=args.private_key)

    return save_dir, upload_dir, public_key, private_key


def poll_image(
    timeout: int,
    camera: gp.Camera,
    save_dir: Path,
    upload_dir: Path,
    public_key: RSA.RsaKey,
):
    global FLAG_UPLOAD, FLAG_OVERWRITE
    spinner_thread.start()

    while True:
        try:
            event_type, event_data = camera.wait_for_event(timeout)
            if event_type == gp.GP_EVENT_FILE_ADDED:
                file_name = event_data.name.removeprefix("capt_")
                cam_file = camera.file_get(
                    event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL
                )

                target_path = save_dir / file_name
                write_sidecar(target_path, ("status", Stage.SAVING))

                save_image(image=cam_file, path=target_path)
                file_status_set(file_name, Stage.WAITING)
                executor.submit(handle_image, target_path, upload_dir, public_key)

        except gp.GPhoto2Error as ex:
            print(f"Camera error: {ex}. Attempting to reconnect...")
            try:
                camera.exit()
            except Exception:
                pass

            time.sleep(2)
            camera = connect_camera()


def handle_image(target_path: Path, upload_dir: Path, public_key: RSA.RsaKey):
    try:
        if FLAG_UPLOAD:
            upload_image(path=target_path, upload_dir=upload_dir)

        if FLAG_DELETE_LOCAL:
            os.remove(target_path)

        if FLAG_ENCRYPT and not FLAG_DELETE_LOCAL:
            write_sidecar(target_path, ("status", Stage.ENCRYPTING))
            file_status_set(target_path.name, Stage.ENCRYPTING)
            encryption.encrypt(
                path=target_path, overwrite=FLAG_OVERWRITE, public_key=public_key
            )

        write_sidecar(target_path, ("status", Stage.DONE))
        file_status_set(target_path.name, Stage.DONE, 100)

        os.remove(get_sidecar_file_path(target_path))

    except Exception as e:
        write_sidecar(target_path, ("stage", Stage.FAILED))
        write_sidecar(target_path, ("reason", e))
        file_status_set(target_path.name, Stage.FAILED)


def save_image(image: gp.CameraFile, path: Path):
    file_status_set(path.name, Stage.SAVING)
    image.save(str(path))


def upload_image(path: Path, upload_dir: Path):
    write_sidecar(path, ("status", Stage.UPLOADING))
    sftp.upload(path, os.path.join(upload_dir, path.name))


def handle_unfinished(save_dir: Path, upload_dir: Path, public_key: RSA.RsaKey):
    print(f"Checking for unfinished files in {save_dir}")
    for file_path in save_dir.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix != ".lock":
            continue

        if not file_path.with_suffix("").exists():
            continue

        lockfile_content = get_key_value(file_path)
        status = lockfile_content.get("status")

        if status == Stage.DONE.value.lower():
            continue

        print(f"Found unfinished file at: {file_path.with_suffix("")}")
        executor.submit(handle_image, file_path.with_suffix(""), upload_dir, public_key)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n Shutting down...")

        print("Stopping Workers...")
        executor.shutdown(wait=True)

        cli.stop_event.set()
        if spinner_thread.is_alive():
            spinner_thread.join()

        print("\nProgram terminated by user.")
