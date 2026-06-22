from xmrsigner.models.base_encoder import (
    BaseQrEncoder,
    BaseStaticQrEncoder
)
from xmrsigner.models.qr_type import QrType
from xmrsigner.helpers.compactseed import CompactSeed

from ots.seed import SeedIndices


class SeedQrEncoder(BaseStaticQrEncoder):

    def __init__(self, indices: SeedIndices):
        super().__init__()
        self.indices: SeedIndices = indices

    def next_part(self) -> str:
        # Output as Numeric data format
        return ''.join([str("%04d" % index) for index in self.indices.values])

    def get_qr_type(self):
        return QrType.SEED_QR


class CompactSeedQrEncoder(SeedQrEncoder):

    def next_part(self) -> bytes:
        return CompactSeed.seedIndices2bytes(self.indices)

    def get_qr_type(self):
        return QrType.COMPACT_SEED_QR
