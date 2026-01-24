import gphoto2 as gp
import time
import os
import sys
import argparse
from pathlib import Path
from cryptography.fernet import Fernet
from enum import Enum
import getpass
from concurrent.futures import ThreadPoolExecutor

import sftp
import encryption

# Globals
FLAG_UPLOAD = None
FLAG_ENCRYPT = None
FLAG_MODE = None
FLAG_OVERWRITE = None

class Mode(Enum):
    STANDARD = "standard"
    DECRYPT = "decrypt"

executor = ThreadPoolExecutor(max_workers=4)

def main():
    global FLAG_UPLOAD, FLAG_MODE, FLAG_OVERWRITE

    save_dir, fernet, upload_dir = args()

    if FLAG_MODE is Mode.DECRYPT:
        encryption.decrypt_dir(save_dir, fernet, FLAG_OVERWRITE)
        return 0

    if FLAG_UPLOAD:
        sftp.connect()

    camera = connect_camera()
    poll_image(timeout=3000, camera=camera, save_dir=save_dir, fernet=fernet, upload_dir=upload_dir)  

    return 0

def args():
    global FLAG_UPLOAD, FLAG_ENCRYPT, FLAG_MODE, FLAG_OVERWRITE

    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default=Mode.STANDARD, type=Mode)
    parser.add_argument("--dir", type=Path, default=Path.cwd())
    parser.add_argument("--upload", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--encrypt", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--key", type=Path, default="camtransfer.key")
    parser.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--upload-dir", type=Path, default="/uploads")

    args = parser.parse_args()

    FLAG_MODE = args.mode
    FLAG_UPLOAD = args.upload
    FLAG_ENCRYPT = args.encrypt
    FLAG_OVERWRITE = args.overwrite
    
    if not args.dir.is_dir():
        parser.error(f"The path {args.dir} is not a valid directory.")

    save_dir = Path(os.path.join(os.getcwd(), args.dir))
    fernet = None
    upload_dir = args.upload_dir
    
    if FLAG_ENCRYPT or FLAG_MODE is Mode.DECRYPT:
        if args.key.exists():
            with open(args.key, "rb") as keyfile:
                fernet = Fernet(keyfile.read())
        else:
            if FLAG_MODE is Mode.DECRYPT:
                parser.error(f"No keyfile exists at {args.key} - please provide one")
            print(f"No keyfile exists at {args.key}, creating one...")
            fernet = encryption.create_key(args.key)

    return save_dir, fernet, upload_dir

def poll_image(timeout: int, camera: gp.Camera, save_dir: Path, upload_dir: Path, fernet: Fernet):
    global FLAG_UPLOAD, FLAG_OVERWRITE

    while True:
        print(f"Waiting for image (timeout: {timeout})")
        try:
            event_type, event_data = camera.wait_for_event(timeout)
            if event_type == gp.GP_EVENT_FILE_ADDED:
                file_name = event_data.name.removeprefix("capt_")
                cam_file = camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)

                target_path = save_dir / file_name

                save_image(image=cam_file, path=target_path)           
                executor.submit(handle_image, target_path, save_dir, upload_dir, fernet)
                
        except gp.GPhoto2Error as ex:
            print(f"Camera error: {ex}. Attempting to reconnect...")
            try:
                camera.exit()
            except Exception:
                pass

            time.sleep(2)
            camera = connect_camera()

def handle_image(target_path: Path, save_dir: Path, upload_dir: Path, fernet: Fernet):
    try:
        if FLAG_UPLOAD:
            upload_image(path=target_path, upload_dir=upload_dir)

        if FLAG_ENCRYPT:
            encrypt_image(path=target_path, fernet=fernet, overwrite=FLAG_OVERWRITE)
            
    except Exception as e:
        print(f"Job failed for {file_name}: {e}")

def save_image(image: gp.CameraFile, path: Path):
    image.save(str(path))
    print(f"Image saved to {path}")

def upload_image(path: Path, upload_dir: Path):
    sftp.upload(path, os.path.join(upload_dir, path.name))

def encrypt_image(path: Path, fernet: Fernet, overwrite: bool):
    encryption.encrypt_file(path, fernet, overwrite)
    print(f"Image at {path} encrypted")

def connect_camera() -> gp.Camera:
    print('Please connect and switch on your camera...')
    camera = gp.Camera()

    while True:
        try:
            camera.init()
        except gp.GPhoto2Error as ex:
            if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                # no camera, try again in 2 seconds
                time.sleep(2)
                continue
            # some other error we can't handle here
            raise
        # operation completed successfully so exit loop
        break

    

    print(f"Camera {get_camera_name(camera)} initialized successfully")

    return camera

def get_camera_name(camera: gp.Camera) -> str:
    summary = str(camera.get_summary())
    model_line = [line for line in summary.split('\n') if 'Model:' in line][0]
    camera_model = model_line.split('Model:')[1].strip()

    return camera_model

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # TODO: cleanup any running saves and uploads
        print("\nProgram terminated by user.")