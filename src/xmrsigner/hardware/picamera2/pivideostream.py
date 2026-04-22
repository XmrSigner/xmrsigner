from picamera2 import Picamera2, MappedArray
from threading import Thread
from time import sleep
from xmrsigner.hardware.interfaces import CameraInterface


class PiVideoStream2:

    def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
        self.camera = Picamera2()
        video_config = self.camera.create_video_configuration(main={"size": resolution, "format": format})
        self.camera.configure(video_config)
        self.frame = None
        self.should_stop = False
        self.is_stopped = True

    def start(self):
        self.camera.start()
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        self.is_stopped = False

    def update(self):
        while not self.should_stop:
            with MappedArray(self.camera) as m:
                self.frame = m.array.copy()
            sleep(1 / self.camera.framerate)
            if self.should_stop:
                self.camera.stop()
                self.should_stop = False
                self.is_stopped = True

    def read(self):
        return self.frame

    def stop(self):
        self.should_stop = True
        while not self.is_stopped:
            sleep(0.01)
