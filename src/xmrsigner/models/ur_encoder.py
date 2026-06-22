from xmrsigner.models.qr_type import QrType
from xmrsigner.models.settings_definition import QrDensity
from xmrsigner.models.base_encoder import BaseQrEncoder
from xmrsigner.helpers.ur2.ur_encoder import UREncoder
from xmrsigner.helpers.ur2.ur import UR


class UrQrEncoder(BaseQrEncoder):

    def __init__(self, ur_type: str, ur_payload: str, qr_density: QrDensity):
        super().__init__()
        self.ur_type: str = ur_type
        self.ur_payload: str = ur_payload
        qr_ur_bytes = UR(self.ur_type, self.ur_payload)
        self.qr_max_fragment_size = {
            QrDensity.LOW: 10,
            QrDensity.MEDIUM: 30,
            QrDensity.HIGH: 120
        }[qr_density]
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)

    def next_part_image(self, width=240, height=240, border=3, background_color='bdbdbd'):
        return self.qr.qrimage_io(  # TODO: why not qr.qrimage instead???
            self.next_part(),
            width,
            height,
            border,
            background_color=background_color
        )

    def seq_len(self):
        return self.ur2_encode.fountain_encoder.seq_len()

    def next_part(self) -> str:
        return self.ur2_encode.next_part().upper()

    @property
    def is_complete(self):
        return self.ur2_encode.is_complete()

    def get_qr_type(self):
        return QrType.UR2
