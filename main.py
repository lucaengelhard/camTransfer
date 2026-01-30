import gphoto2 as gp
import time
import os
import sys
from pathlib import Path
from Crypto.PublicKey import RSA
from enum import Enum
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
    get_sidecar_file_path,
    get_key_value,
    write_sidecar,
)
from global_values import FLAGS, FlagType, Mode
from threads import executor, spinner_thread


def main():
    global FLAGS

    save_dir, upload_dir, public_key, private_key = cli.args()

    if FLAGS[FlagType.MODE] is Mode.CREATE_KEYS:
        return 0

    if FLAGS[FlagType.MODE] is Mode.DECRYPT:
        encryption.decrypt_dir(save_dir, private_key, FLAGS[FlagType.OVERWRITE])
        return 0

    if FLAGS[FlagType.UPLOAD]:
        sftp.test_connection()

    if FLAGS[FlagType.HANDLE_UNFINISHED]:
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


def poll_image(
    timeout: int,
    camera: gp.Camera,
    save_dir: Path,
    upload_dir: Path,
    public_key: RSA.RsaKey,
):
    global FLAGS
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
        if FLAGS[FlagType.UPLOAD]:
            upload_image(path=target_path, upload_dir=upload_dir)

        if FLAGS[FlagType.DELETE_LOCAL]:
            os.remove(target_path)

        if FLAGS[FlagType.ENCRYPT] and not FLAGS[FlagType.DELETE_LOCAL]:
            write_sidecar(target_path, ("status", Stage.ENCRYPTING))
            file_status_set(target_path.name, Stage.ENCRYPTING)
            encryption.encrypt(
                path=target_path,
                overwrite=FLAGS[FlagType.OVERWRITE],
                public_key=public_key,
            )

        file_status_set(target_path.name, Stage.DONE, 100)

        os.remove(get_sidecar_file_path(target_path))

    except Exception as e:
        write_sidecar(target_path, ("status", Stage.FAILED))
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
