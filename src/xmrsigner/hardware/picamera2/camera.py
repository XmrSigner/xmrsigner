from picamera2 import Picamera2
from PIL.Image import Image
from numpy import ndarray as NumpyArray
from xmrsigner.hardware.interfaces import CameraInterface
from xmrsigner.models.settings import Settings, Setting
from xmrsigner.hardware.picamera2.pivideostream import PiVideoStream2


class Camera(CameraInterface):

    @classmethod
    def get_instance(cls) -> 'Camera':
        # This is the only way to access the one and only Controller
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance._video_stream = None
            cls._instance._picamera = Picamera2()
        cls._instance._camera_rotation = int(Settings.get_instance().get_value(Setting.CAMERA_ROTATION))
        return cls._instance

    def start_video_stream_mode(
        self,
        resolution: tuple[int, int] = (512, 384),
        framerate: int = 12,
        format: str = 'bgr'
    ) -> None:
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        self._video_stream = PiVideoStream2(resolution=resolution, framerate=framerate, format=format)
        self._video_stream.start()

    def read_video_stream(self, as_image: bool = False) -> Image|NumpyArray:
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        frame = self._video_stream.read()
        if not as_image:
            return frame
        if frame is None:
            return None
        return Image.fromarray(frame.astype('uint8'), 'RGB').rotate(90 + self._camera_rotation)

    def stop_video_stream_mode(self) -> None:
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None

    def start_single_frame_mode(self, resolution: tuple[int, int] = (720, 480)) -> None:
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._picamera is not None:
            self._picamera.stop()
        self._picamera.configure(self._picamera.create_still_configuration(main={"size": resolution}))
        self._picamera.start()

    def capture_frame(self) -> Image:
        if self._picamera is None:
            raise Exception("Must call start_single_frame_mode first.")
        return Image.fromarray(self._picamera.capture_array()).rotate(90 + self._camera_rotation)

    def stop_single_frame_mode(self) -> None:
        if self._picamera is not None:
            self._picamera.stop()
