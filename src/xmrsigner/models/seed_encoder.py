from xmrsigner.models.base_encoder import (
    BaseQrEncoder,
    BaseStaticQrEncoder
)
from xmrsigner.models.qr_type import QrType
from xmrsigner.helpers.compactseed import CompactSeed


class SeedQrEncoder(BaseStaticQrEncoder):

    def __init__(self, seed_phrase: list[str], wordlist: list[str]):
        super().__init__()
        self.seed_phrase = seed_phrase
        self.wordlist: list[str] = wordlist
        if not self.wordlist:
            raise Exception('Wordlist Required')

    def next_part(self):
        data = ""
        # Output as Numeric data format
        for word in self.seed_phrase:
            index = self.wordlist.index(word)
            data += str("%04d" % index)
        return data

    def get_qr_type(self):
        return QrType.SEED_QR


class CompactSeedQrEncoder(SeedQrEncoder):

    def next_part(self):
        seed_phrase = self.seed_phrase.copy()
        if len(seed_phrase) in (13, 25):  # monero seed with checksum word, remove checksum word at the end
            del seed_phrase[-1]
        if len(seed_phrase) not in (12, 16, 24):  # results in (16, 22, 32) bytes per seed
            raise Exception('Neither a monero seed nor a polyseed!')
        return CompactSeed(self.wordlist).bytes(seed_phrase)

    def get_qr_type(self):
        return QrType.COMPACT_SEED_QR
