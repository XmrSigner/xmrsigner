from dataclasses import dataclass
from xmrsigner.helpers.qr import Qr
from xmrsigner.models.settings_definition import QrDensity


@dataclass
class QrEncoder:
    """
    Encode data for displaying as qr image
    """
    qr: Qr|None = None
    qr_density: QrDensity = QrDensity.MEDIUM
    _complete: bool = False

    def __post_init__(self):
        self.qr = Qr()

    def seq_len(self):
        raise Exception("Not implemented in child class")

    def total_parts(self) -> int:
        return self.seq_len()

    def next_part(self):
        raise Exception("Not implemented in child class")

    def next_part_image(self, width=240, height=240, border=3, background_color="bdbdbd"):
        raise Exception("Not implemented in child class")

    def get_qr_density(self):
        return self.qr_density

    def get_qr_type(self):
        raise Exception("Not implemented in child class")

    @property
    def qr_type(self) -> str:
        return self.get_qr_type()

    @property
    def is_complete(self):
        return self._complete

class BaseQrEncoder(QrEncoder):

    def next_part(self) -> str:
        raise Exception("Not implemented in child class")

    @property
    def is_complete(self):
        raise Exception("Not implemented in child class")

    def _create_parts(self):
        raise Exception("Not implemented in child class")


class BaseStaticQrEncoder(BaseQrEncoder):

    def seq_len(self):
        return 1

    @property
    def is_complete(self):
        return True

    def next_part_image(self, width=240, height=240, border=3, background_color="bdbdbd"):
        return self.qr.qrimage(self.next_part(), width, height, border, background_color=f'#{background_color}')
