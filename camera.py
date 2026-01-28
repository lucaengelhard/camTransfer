import gphoto2 as gp
import time

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
