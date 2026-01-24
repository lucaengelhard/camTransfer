import gphoto2 as gp
import time
import os
import sys
import argparse
from pathlib import Path


import sftp

# Globals
FLAG_UPLOAD = True

def main():
    global FLAG_UPLOAD

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=Path.cwd())
    parser.add_argument("--upload", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.upload is not None:
        FLAG_UPLOAD = args.upload

    if not args.dir.is_dir():
        parser.error(f"The path {args.dir} is not a valid directory.")

    if FLAG_UPLOAD:
        sftp.connect()

    # Set up dir
    save_dir = Path(os.path.join(os.getcwd(), args.dir))

    camera = connect_camera()
    poll_image(timeout=3000, camera=camera, save_dir=save_dir)  

    return 0

def poll_image(timeout: int, camera: gp.Camera, save_dir: Path):
    global FLAG_UPLOAD

    while True:
        print(f"Waiting for image (timeout: {timeout})")
        try:
            event_type, event_data = camera.wait_for_event(timeout)
            if event_type == gp.GP_EVENT_FILE_ADDED:
                cam_file = camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                file_name = event_data.name.removeprefix("capt_")
                target_path = Path(os.path.join(save_dir, file_name))
                save_image(image=cam_file, path=target_path)
                if FLAG_UPLOAD: 
                    upload_image(path=target_path)
                
        except gp.GPhoto2Error as ex:
            print(f"Camera error: {ex}. Attempting to reconnect...")
            try:
                camera.exit()
            except Exception:
                pass

            time.sleep(2)
            camera = connect_camera()

def save_image(image: gp.CameraFile, path: Path):
    print(f"Image is being saved to {path}")
    image.save(str(path))

def upload_image(path: Path):
    print(f"Image {path.name} is being uploaded")
    sftp.upload(path, os.path.join("/uploads", path.name))

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
    sys.exit(main())