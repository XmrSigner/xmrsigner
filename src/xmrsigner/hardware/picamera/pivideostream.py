from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread
from time import sleep

from xmrsigner.hardware.interfaces import PiVideoStreamInterface


# Modified from: https://github.com/jrosebr1/imutils
class PiVideoStream(PiVideoStreamInterface):

    def __init__(
        self,
        resolution: tuple[int, int] = (320, 240),
        framerate: int = 32,
        format: str = 'bgr',
        **kwargs
    ):
        # initialize the camera
        self.camera = PiCamera(resolution=resolution, framerate=framerate, **kwargs)

        # initialize the stream
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
                                                     format=format, use_video_port=True)

        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.should_stop = False
        self.is_stopped = True

    def start(self) -> None:
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        self.is_stopped = False

    def update(self) -> None:
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.should_stop:
                print("PiVideoStream: closing everything")
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                self.should_stop = False
                self.is_stopped = True
                return

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self) -> None:
        # indicate that the thread should be stopped
        self.should_stop = True

        # Block in this thread until stopped
        while not self.is_stopped:
            sleep(0.01)
