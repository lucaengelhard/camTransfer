import gphoto2 as gp
import time
import os
import sys
import argparse
import encryption
from pathlib import Path

def main():
    # Set up dir
    save_dir = os.path.join(os.getcwd(), 'images')
    os.makedirs(save_dir, exist_ok=True)

    camera = connect_camera()
    poll_image(timeout=3000, camera=camera)

    return 0

def poll_image(timeout: int, camera: gp.Camera):
    while True:
        print(f"Waiting for image (timeout: {timeout})")
        try:
            event_type, event_data = camera.wait_for_event(timeout)
            if event_type == gp.GP_EVENT_FILE_ADDED:
                cam_file = camera.file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                target_path = os.path.join(os.getcwd(), event_data.name.removeprefix("capt_"))
                save_image(image=cam_file, path=target_path)
                
        except gp.GPhoto2Error as ex:
            print(f"Camera error: {ex}. Attempting to reconnect...")
            try:
                camera.exit()
            except Exception:
                pass

            time.sleep(2)
            camera = connect_camera()

def save_image(image: gp.CameraFile, path: os.path):
    print(f"Image is being saved to {path}")
    image.save(path)

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

def path_or_none(value):
    """Custom type function for argparse: accepts empty or a valid file path."""
    if not value:
        return None
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid file path")
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--key",
        type=path_or_none,
        default=None,
        help="What key to use, if empty generates a new one"
    )
    args = parser.parse_args()

    key = encryption.get_key(args.key)
    print(key)
    
    sys.exit(main())