from ots.seed import (
    SeedLanguage,
    LegacySeed,
    MoneroSeed,
    Polyseed
)
from ots.enums import SeedType

from xmrsigner.models.base_decoder import BaseSingleFrameQrDecoder, DecodeQRStatus
from xmrsigner.models.qr_type import QrType
from xmrsigner.helpers.seedwordindex import SeedWordIndex  # TODO: remove!
from xmrsigner.helpers.compactseed import CompactSeed
from xmrsigner.models.wordlists import words


class SeedQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes single frame representing a seed.
        Supports XmrSigner SeedQR numeric (wordlist indices) representation of a seed.
        Supports XmrSigner CompactSeedQR entropy byte representation of a seed.
        Supports mnemonic seed phrase string data.
    """
    def __init__(self, wordlist_language):
        super().__init__()
        self.seed_phrase: list[str] = []
        self.wordlist_language= wordlist_language

    def add(self, segment, qr_type=QrType.SEED_QR):
        # `segment` data will either be bytes or str, depending on the qr_type
        if qr_type == QrType.SEED_QR:
            print('SeedQrDecoder.add(): SEED__SEEDQR')
            try:
                num_words = int(len(segment) / 4)
                # Parse 12, 13, 16, 24 or 25-word QR code
                print(f'num_words: {num_words}')
                if num_words not in (12, 13, 16, 24, 25):
                    return DecodeQRStatus.INVALID
                wordlist = words(SeedType.POLYSEED if num_words == 16 else SeedType.MONERO, SeedLanguage.fromCode('en'))
                seed_words = SeedWordIndex(wordlist).from_indices_string(segment)
                self.seed_phrase = MoneroSeed.decode(' '.join(seed_words).phrase(SeedLanguage.fromCode('en')).insecure().split()) if len(seed_words) in (12, 24) else seed_words  # if there are only 12/24 words the checksum word is missing and we add it
                if self.is_validphrase_word_count():
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
            except Exception as e:
                print(f'SeedQrDecoder.add(): SEED__SEEDQR: {e}')
            return DecodeQRStatus.INVALID
        if qr_type == QrType.COMPACT_SEED_QR:
            print('SeedQrDecoder.add(): SEED__COMPACTSEEDQR')
            try:
                word_count = CompactSeed.length(segment)
                if word_count == 12:  # Monero Legacy seed
                    wordlist = words(SeedType.MONERO, SeedLanguage.fromCode('en'))
                    self.seed_phrase = LegacySeed.decode(' '.join(CompactSeed(wordlist).words(segment))).phrase(SeedLanguage.fromCode('en')).insecure().split()  # convert direct to 13 words
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                if word_count == 24:  # Monero seed
                    wordlist = words(SeedType.MONERO, SeedLanguage.fromCode('en'))
                    self.seed_phrase = MoneroSeed.decode(' '.join(CompactSeed(wordlist).words(segment))).phrase(SeedLanguage.fromCode('en')).insecure().split()  # convert direct to 25 words
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                if wordcount == 16:  # Polyseed
                    wordlist = words(SeedType.POLYSEED, SeedLanguage.fromCode('en'))
                    self.seed_phrase = CompactSeed(wordlist).words(segment)
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
            except Exception as e:
                logger.exception(repr(e))
            return DecodeQRStatus.INVALID
        if qr_type == QrType.MNEMONIC:
            print('SeedQrDecoder.add(): SEED__MNEMONIC')
            try:
                seed_words: str = segment.strip()
                word_count: int = len(seed_words.split(' '))
                valid_seed: bool = False
                try:
                    if word_count in (24, 25):  # Monero seed phrase
                        MoneroSeed.decode(seed_words)
                    if word_count in (12, 13):  # Monero seed phrase
                        LegacySeed.decode(seed_words)
                    if word_count == 16:  # polyseed
                        Polyseed.decode(seed_phrase_list, password='test')  # we use the fact that a password if not is necessary is not used to check if it is a valid polyseed with or without password
                    valid_seed = True
                except:
                    pass
                if valid_seed:
                    self.seed_phrase = seed_words.split()
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
            except Exception as e:
                pass
            return DecodeQRStatus.INVALID
        print(f'SeedQrDecoder.add(): end')
        return DecodeQRStatus.INVALID

    def get_seed_phrase(self) -> list[str]:
        return self.seed_phrase if self.complete else []

    def is_validphrase_word_count(self) -> bool:
        return len(self.seed_phrase) in (13, 16, 25)
