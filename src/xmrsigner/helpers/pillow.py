from PIL import ImageFont
from PIL import __version__ as pil_version


PILLOW_VERSION = pil_version.split('.')

def get_font_size(font: ImageFont, text: str) -> tuple[int, int]:  # width, height
    if int(PILLOW_VERSION[0]) < 10:
        return font.getsize(text)
    box = font.getbbox(text)
    return (font.getlength(text), box[3] - box[1])
