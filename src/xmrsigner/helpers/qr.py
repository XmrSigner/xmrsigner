from xmrsigner.gui.components import Theme
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_L
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer
)
from PIL import Image
from subprocess import call
from enum import Enum


class QrStyle(Enum):
    DEFAULT = 1
    ROUNDED = 2
    GRID = 3


class Qr:

    def __init__(self) -> None:
        pass

    def qrimage(
            self,
            data,
            width: int = 240,
            height: int = 240,
            border: int = 3,
            style: QrStyle = QrStyle.DEFAULT,
            background_color: str = '#444'
    ):
        qr = QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=5,
            border=border
        )
        qr.add_data(data)
        qr.make(fit=True)
        if style == QrStyle.DEFAULT:
            return qr.make_image(
                fill_color=Theme.QRCODE_FILL_COLOR,
                back_color=background_color
            ).resize((width,height)).convert('RGBA')
        if style == QrStyle.ROUNDED:
            return qr.make_image(
                fill_color=Theme.QRCODE_FILL_COLOR,
                back_color=background_color,
                image_factory=StyledPilImage,
                module_drawer=CircleModuleDrawer()
            ).resize((width,height)).convert('RGBA')
        if style == QrStyle.GRID:
            return qr.make_image(
                fill_color=Theme.QRCODE_FILL_COLOR,
                back_color=background_color,
                image_factory=StyledPilImage,
                module_drawer=GappedSquareModuleDrawer()
            ).resize((width,height)).convert('RGBA')

    # TODO: why??? Remove, is there is not a very good reason for it...
    def qrimage_io(self, data, width=240, height=240, border=3, background_color="808080"):
        cmd = f"""qrencode -m {str(border) if 1 <= border <= 10 else '3'} -s 3 -l L --foreground=000000 --background={background_color} -t PNG -o "/tmp/qrcode.png" "{str(data)}" """  # TODO: WTF, implement in python? Check what was the reason or if i makes any sense.
        rv = call(cmd, shell=True)
        # if qrencode fails, fall back to only encoder
        if rv != 0:
            return self.qrimage(data, width, height, border)
        img = Image.open("/tmp/qrcode.png").resize((width,height), Image.NEAREST).convert("RGBA")
        return img
