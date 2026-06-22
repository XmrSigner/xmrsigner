from re import search
from datetime import date, datetime

from xmrsigner.models.base_decoder import BaseSingleFrameQrDecoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.base_decoder import DecodeQRStatus


class TimestampQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a timestamp
    """

    def __init__(self):
        super().__init__()
        self.timestamp: int|None = None

    def add(self, segment: str, qr_type=QrType.DATE):
        r = search(r'^timestamp:(\d+)$', segment)
        if r != None:
            try:
                self.timestamp = int(r.group(1))
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except:
                pass
        return DecodeQRStatus.INVALID

    @property
    def datetime(self) -> datetime|None:
        if self.timestamp is None:
            return None
        return datetime.fromtimestamp(self.timestamp)

    @property
    def date(self) -> date|None:
        if self.timestamp is None:
            return None
        return self.datetime.date()

    @staticmethod
    def is_timestamp(s: str) -> bool:
        try:
            return search(r'^timestamp:(\d+)$', s) is not None
        except:
            return False
