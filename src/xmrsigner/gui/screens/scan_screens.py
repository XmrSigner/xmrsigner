from ots.address import Address
from time import sleep

from dataclasses import dataclass
from PIL import Image, ImageDraw

from xmrsigner.gui import renderer
from xmrsigner.hardware.buttons import HardwareButtonsConstants
from xmrsigner.hardware.camera import Camera
from xmrsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from xmrsigner.models.threads import BaseThread
from xmrsigner.gui.screens.screen import (
    BaseScreen,
    BaseTopNavScreen,
    ButtonListScreen,
    LargeIconStatusScreen
)
from xmrsigner.gui.constants import Padding
from xmrsigner.gui.constants import Icon as IconConstants
from xmrsigner.gui.components import Theme, Fonts, TextArea


@dataclass
class ScanScreen(BaseScreen):
    """
    Live preview has to balance three competing threads:
    * Camera capturing frames and making them available to read.
    * Decoder analyzing frames for QR codes.
    * Live preview display writing frames to the screen.

    All of this would ideally be rewritten as in C/C++/Rust with python bindings for
    vastly improved performance.

    Until then, we have to balance the resources the Pi Zero has to work with. Thus, we
    set a modest fps target for the camera: 5fps. At this pace, the decoder and the live
    display can more or less keep up with the flow of frames without much wasted effort
    in any of the threads.

    Note: performance tuning was targeted for the Pi Zero.

    The resolution (480x480) has not been tweaked in order to guarantee that our
    decoding abilities remain as-is. It's possible that more optimizations could be made
    here (e.g. higher res w/no performance impact? Lower res w/same decoding but faster
    performance? etc).

    Note: This is quite a lot of important tasks for a Screen to be managing; much of
    this should probably be refactored into the Controller.
    """
    decoder: DecodeQR = None
    instructions_text: str = None
    resolution: tuple[int,int] = (480, 480)
    framerate: int = 5
    render_rect: tuple[int,int,int,int] = None

    def __post_init__(self):
        from xmrsigner.hardware.camera import Camera
        # Initialize the base class
        super().__post_init__()
        self.instructions_text = "< back  |  " + self.instructions_text
        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=self.resolution, framerate=self.framerate, format="rgb")
        self.threads.append(ScanScreen.LivePreviewThread(
            camera=self.camera,
            decoder=self.decoder,
            renderer=self.renderer,
            instructions_text=self.instructions_text,
            render_rect=self.render_rect,
        ))


    class LivePreviewThread(BaseThread):

        def __init__(self, camera: Camera, decoder: DecodeQR, renderer: renderer.Renderer, instructions_text: str, render_rect: tuple[int,int,int,int]):
            self.camera = camera
            self.decoder = decoder
            self.renderer = renderer
            self.instructions_text = instructions_text
            if render_rect:
                self.render_rect = render_rect
            else:
                self.render_rect = (0, 0, self.renderer.canvas_width, self.renderer.canvas_height)
            self.render_width = self.render_rect[2] - self.render_rect[0]
            self.render_height = self.render_rect[3] - self.render_rect[1]
            super().__init__()

        def run(self):
            from timeit import default_timer as timer
            instructions_font = Fonts.get_font(Theme.BODY_FONT_NAME, Theme.BUTTON_FONT_SIZE)
            while self.keep_running:
                start = timer()
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    scan_text = self.instructions_text
                    if self.decoder and self.decoder.get_percent_complete() > 0 and self.decoder.is_ur:
                        scan_text = str(self.decoder.get_percent_complete()) + "% Complete"
                    with self.renderer.lock:
                        if frame.width > self.render_width or frame.height > self.render_height:
                            frame = frame.resize(
                                (self.render_width, self.render_height),
                                resample=Image.NEAREST  # Use nearest neighbor for max speed
                            )
                        draw = ImageDraw.Draw(frame)
                        if scan_text:
                            # Note: shadowed text (adding a 'stroke' outline) can
                            # significantly slow down the rendering.
                            # Temp solution: render a slight 1px shadow behind the text
                            draw.text(xy=(
                                        int(self.renderer.canvas_width / 2 + 2),
                                        self.renderer.canvas_height - Padding.EDGE + 2
                                     ),
                                     text=scan_text,
                                     fill=Theme.BRIGHTNESS_TEXT_COLOR,
                                     font=instructions_font,
                                     anchor="ms")
                            # Render the onscreen instructions
                            draw.text(xy=(
                                        int(self.renderer.canvas_width/2),
                                        self.renderer.canvas_height - Padding.EDGE
                                     ),
                                     text=scan_text,
                                     fill=Theme.BODY_FONT_COLOR,
                                     font=instructions_font,
                                     anchor="ms")
                        self.renderer.show_image(frame, show_direct=True)
                sleep(0.05) # turn this up or down to tune performance while decoding UR
                if self.camera._video_stream is None:
                    break


    def _run(self):
        """
        _render() is mostly meant to be a one-time initial drawing call to set up the
        Screen. Once interaction starts, the display updates have to be managed in
        _run(). The live preview is an extra-complex case.
        """
        while True:
            frame = self.camera.read_video_stream()
            if frame is not None:
                status = self.decoder.add_image(frame)
                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break


@dataclass
class ScanViewOnlyWalletScreen(LargeIconStatusScreen):
    address: Address|None = None

    def __post_init__(self):
        if self.address is None:
            raise Exception('Wallet address is missing.')
        self.show_back_button = False
        self.title = 'View only Wallet!'
        self.status_icon_name = IconConstants.ERROR
        self.status_icon_size = Theme.ICON_PRIMARY_SCREEN_SIZE
        self.status_color = Theme.WARNING_COLOR
        self.status_headline = f'\nWallet {self.address.fingerprint} ({self.address.base58[:6]}...{self.address.base58[-6:]}) is view only!'
        super().__post_init__()
