from hashlib import sha256
from os import popen
from time import time
from PIL.Image import Image


class Entropy:

    hash_bytes: bytes|None = None

    def hw_entropy(self) -> bytes:
        try:
            stream = popen('cat /proc/cpuinfo | grep Serial')
            output = stream.read()
            return output.split(':')[-1].strip().encode()
        except Exception as e:
            print(f'hw_entropy: failed!')
            print(repr(e))
        return b'0'

    def millis_entropy(self) -> bytes:
        # Build in modest entropy via millis since power on
        t: int = int(str(time).replace('.', ''))
        return b''.join([
            int.to_bytes(t>>i & 255)
            for i in range(i.bit_length() // 8)
        ])

    def sha256_chain(self, data: bytes) -> bytes:
        self.hash_bytes = sha256((self.hash_bytes or b'') + data).digest()
        return self.hash_bytes

    def __bytes__(self) -> bytes:
        if self.hash_bytes is None:
            self.sha256_chain(self.hw_entropy())
            self.sha256_chain(self.millis_entropy())
        return self.hash_bytes


class CameraEntropy(Entropy):

    _preview_images_bytes: list[bytes]
    _seed_entropy_image_bytes: bytes

    def __init__(
        self,
        preview_images: list[Image],
        seed_entropy_image: Image
    ):
        self._preview_images_bytes = [img.tobytes() for img in preview_images]
        self._seed_entropy_image_bytes = seed_entropy_image.tobytes()

    def __bytes__(self) -> bytes:
        if self.hash_bytes is None:
            super().__bytes__()
            for chunk in self._preview_images_bytes:
                self.sha256_chain(chunk)
            self.sha256_chain(self._seed_entropy_image_bytes)
        return self.hash_bytes


class VerifyableEntropy(Entropy):

    def __bytes__(self) -> bytes:
        raise Exception('No entropy here, needs to be overwriten!')


class DiceEntropy(VerifyableEntropy):

    def __init__(self, dices: str|list[int], target_entropy: int = 256, dice_sides: int = 6):
        if (dice_sides**len(dices)) < (2**target_entropy):
            raise ValueError('Not enough input entropy for the desired output entropy')
        if type(dices) != str:
            dices = ''.join([str(dice) for dice in dices])
        self.hash_bytes = self.sha256_chain(dices.encode())

    def __bytes__(self) -> bytes:
        return self.hash_bytes
