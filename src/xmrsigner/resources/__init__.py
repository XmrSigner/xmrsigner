from os.path import dirname, exists, join
from base64 import b85decode
from lzma import decompress as lzma


def get(namespace, name):
    file_path = join(dirname(__file__), namespace, name)
    if exists(file_path):
        with open(file_path, 'rb') as file:
            return file.read()
    try:
        if namespace == 'icons':
            from . import icons
            return lzma(b85decode(icons.data[name]))
        if namespace == 'fonts':
            from . import fonts
            return lzma(b85decode(fonts.data[name]))
        if namespace == 'img':
            from . import img
            return lzma(b85decode(img.data[name]))

        raise ImportError(f'Namespace not found: {namespace}')
    except (ImportError, KeyError):
        raise FileNotFoundError(f'Resource not found: {namespace}/{name}')
