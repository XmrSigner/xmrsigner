from PIL.Image import Image
from numpy import array as NumpyArray

from xmrsigner.models.singleton import Singleton


class CameraInterface(Singleton):

    @classmethod
    def get_instance(cls) -> 'CameraInterface':
        pass

    def start_video_stream_mode(
        self,
        resolution: tuple[int, int] = (512, 384),
        framerate: int = 12,
        format: str = 'bgr'
    ) -> None:
        pass

    def read_video_stream(self, as_image: bool = False) -> Image|NumpyArray:
        pass

    def stop_video_stream_mode(self) -> None:
        pass

    def start_single_frame_mode(self, resolution: tuple[int, int] = (720, 480)) -> None:
        pass

    def capture_frame(self) -> Image:
        pass

    def stop_single_frame_mode(self) -> None:
        pass


class PiVideoStreamInterface:

    def __init__(
            self,
            resolution: tuple[int, int] = (320, 240),
            framerate: int = 32,
            format: str = 'bgr',
            **kwargs
            ):
        pass

    def update(self) -> None:
        pass

    def read(self) -> NumpyArray:
        pass

    def stop(self) -> None:
        pass
