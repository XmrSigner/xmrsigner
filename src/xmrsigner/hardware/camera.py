from numpy import array as NumpyArray
from PIL.Image import Image

from xmrsigner.hardware.interfaces import CameraInterface
try:
    import picamera2
    from xmrsigner.hardware.picamera2.camera import Camera as CameraImplementation
    print('=> backend: picamera2')
except Exception:
    import picamera
    from xmrsigner.hardware.picamera.camera import Camera as CameraImplementation
    print('=> backend: picamera')


class Camera(CameraInterface):

    @classmethod
    def get_instance(cls) -> 'Camera':
        print('=>get camera<=')
        return CameraImplementation.get_instance()

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
