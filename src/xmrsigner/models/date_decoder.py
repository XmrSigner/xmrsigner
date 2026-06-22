from re import search
from datetime import date

from xmrsigner.models.base_decoder import BaseSingleFrameQrDecoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.base_decoder import DecodeQRStatus


class DateQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a date
    """

    def __init__(self):
        super().__init__()
        self.date: date|None = None

    def add(self, segment: str, qr_type=QrType.DATE):
        r = search(r'^date:(\d{4}-\d{2}-\d{2})$', segment)
        if r != None:
            try:
                self.date = date.fromisoformat(r.group(1))
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except:
                pass
        return DecodeQRStatus.INVALID

    @staticmethod
    def is_date(s: str) -> bool:
        try:
            return search(r'^date:\d{4}-\d{2}-\d{2}$', s) is not None
        except:
            return False
