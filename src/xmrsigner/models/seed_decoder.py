from ots.seed import (
    Seed,
    SeedIndices,
    LegacySeed,
    MoneroSeed,
    Polyseed,
    OtsPolyseedNoPasswordProvidedException
)
from ots.enums import SeedType

from xmrsigner.models.base_decoder import BaseSingleFrameQrDecoder, DecodeQRStatus
from xmrsigner.models.qr_type import QrType
from xmrsigner.helpers.compactseed import CompactSeed


class SeedQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a seed.
    Supports XmrSigner SeedQR numeric (wordlist indices) representation of a seed.
    Supports XmrSigner CompactSeedQR entropy byte representation of a seed.
    """
    def __init__(self):
        super().__init__()
        self.seed_indices: SeedIndices|None = None
        self.password_required: bool = False

    def add(
        self,
        segment: str|bytes|None,
        qr_type=QrType.SEED_QR
    ) -> DecodeQRStatus:
        # `segment` data will either be bytes or str, depending on the qr_type
        if qr_type == QrType.SEED_QR:
            print('SeedQrDecoder.add(): SEED_QR')
            try:
                si: SeedIndices = SeedIndices.fromString(segment.strip() if isinstance(segment, str) else segment.decode().strip())
                # Parse 12, 13, 16, 24 or 25-word QR code
                print(f'seed words: {si.count}')
                if si.count in (12, 13):
                    LegacySeed.decodeIndices(si)
                if si.count in (24, 25):
                    MoneroSeed.decodeIndices(si)
                if si.count == 16:
                    Polyseed.decodeIndices(si)
                self.seed_indices = si
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except OtsPolyseedNoPasswordProvidedException as npe:
                self.seed_indices = si
                self.password_required = True
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                print(f'SeedQrDecoder.add(): SEED_QR: {e}')
            return DecodeQRStatus.INVALID
        if qr_type == QrType.COMPACT_SEED_QR:
            print('SeedQrDecoder.add(): COMPACT_SEED_QR')
            try:
                si: SeedIndices = CompactSeed.bytes2seedIndices(segment)
                print(f'seed_decoder: seed indices: {si.values}')
                if si.count not in (12, 24, 16):
                    return DecodeQRStatus.INVALID
                if si.count == 12:  # Monero Legacy seed
                    LegacySeed.decodeIndices(si)
                if si.count == 24:  # Monero seed
                    MoneroSeed.decodeIndices(si)
                if si.count == 16:  # Polyseed
                    Polyseed.decodeIndices(si)
                self.seed_indices = si
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except OtsPolyseedNoPasswordProvidedException as npe:
                self.seed_indices = si
                self.password_required = True
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                logger.exception(repr(e))
            return DecodeQRStatus.INVALID
        print(f'SeedQrDecoder.add(): end')
        return DecodeQRStatus.INVALID


class MnemonicQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a seed phrase.
    Supports mnemonic seed phrase string data.
    """
    def __init__(self):
        super().__init__()
        self.seed_phrase: list[str]|None = None
        self.password_required: bool = False

    def add(
        self,
        segment: str|bytes|None,
        qr_type=QrType.SEED_QR
    ) -> DecodeQRStatus:
        # `segment` data will either be bytes or str, depending on the qr_type
        if qr_type == QrType.MNEMONIC:
            print('SeedQrDecoder.add(): MNEMONIC')
            try:
                seed_words: str = segment.strip() if isinstance(segment, str) else segment.decode().strip()
                word_count: int = len(seed_words.split(' '))
                valid_seed: bool = False
                try:
                    if word_count in (24, 25):  # Monero seed phrase
                        MoneroSeed.decode(seed_words)
                    if word_count in (12, 13):  # Monero seed phrase
                        LegacySeed.decode(seed_words)
                    if word_count == 16:  # polyseed
                        Polyseed.decode(seed_words)
                    valid_seed = True
                except OtsPolyseedNoPasswordProvidedException as npe:
                    self.seed_phrase = seed_words.split()
                    self.password_required = True
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                except:
                    pass
                if valid_seed:
                    self.seed_phrase = seed_words.split()
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
            except Exception as e:
                logger.exception(repr(e))
            return DecodeQRStatus.INVALID
        print(f'MnemonicQrDecoder.add(): end')
        return DecodeQRStatus.INVALID
