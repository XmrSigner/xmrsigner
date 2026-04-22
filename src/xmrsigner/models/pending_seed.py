from ots.enums import Network, SeedType


class PendingSeed:

    def __init__(
        self,
        mnemonic: list[str] = []
        type: SeedType = SeedType.MONERO,
        network: Network = Network.MAIN,
        password: str = '',  # key encryption password for Polyseed
        passphrase: str = '',  # offset passphrase for MoneroSeed and Polyseed, LegacySeed is not supported
        height: int = 0,
        isLegacy: bool = False
    ):
        self._mnemonic: list[str|None] = mnemonic
        self.type: SeedType = type
        self.network: Network = network,
        self.height: int = height
        self.isLegacy: bool = isLegacy
        self._mnemonic += [None] * (self.length_expected - self.length)

    @property
    def length_expected(self) -> int:
        if self.type == SeedType.MONERO:
            return 13 if self.isLegacy else 25
        return 16

    @property
    def mnemonic(self) -> str:
        if not self.complete:
            raise Exception('Mnemonic incomplete')
        return ' '.join(self._mnemonic)

    @mnemonic.setter
    def mnemonic(self, phrase: str) -> None:
        self.update(phrase.split())

    def update(self, words: list[str|None]) -> None:
        if len(words) != self.length_expected:
            raise Exception(f'Mnemonic length missmatch, got {len(words)} but expected {self.length_expected}!')
        self._mnemonic = words.copy()

    @property
    def mnemonic_without_checksum(self) -> str:
        if self.type == SeedType.POLYSEED:
            return self.mnemonic
        if not self.complete_without_checksum:
            raise Exception('Mnemonic incomplete')
        return ' '.join(self._mnemonic[:-1])

    @property
    def length(self) -> int:
        return len(self._mnemonic)

    @property
    def missing(self) -> int:
        return sum([1 if w is None else 0 for w in self._mnemonic])

    @property
    def first_missing_index(self) -> int|None:
        try:
            return self._mnemonic.index(None)
        except:
            return None

    @property
    def complete(self) -> bool:
        return self.missing == 0

    @property
    def complete_without_checksum(self) -> bool:
        if self.type == SeedType.POLYSEED:
            return self.complete
        return self.complete or (
            self.missing == 1 and self._mnemonic[-1] == None
        )

    def clear(self) -> None:
        self._mnemonic.clear()
        self._mnemonic += [None] * self.length_expected

    def set(self, word: str, index: int) -> None:
        self._mnemonic[index] = word

    def get(self, index: int) -> str:
        return self._mnemonic[index]

    def seed(
        self,
        without_checksum: bool = False
    ) -> Seed:
        if (
            (self.missing > 0
             and not (
                 without_checksum
                 and self.type == SeedType.MONERO
                 )
             )
            or (self.missing > 1 or self._mnemonic[-1] is not None)
        ):
            raise Exception('Missing words in mnemonic')
        if self.type == SeedType.POLYSEED:
            return Polyseed.decode(
                self.mnemonic,
                network=self.network,
                password=self.password,
                passphrase=self.passphrase
            )
        if self.isLegacy:
            return LegacySeed.decode(
                self.mnemonic if not without_checksum else self.mnemonic_without_checksum,
                network=self.network,
                height=self.height
            )
        return MoneroSeed.decode(
                self.mnemonic if not without_checksum else self.mnemonic_without_checksum,
                network=self.network,
                height=self.height,
                passphrase=self.passphrase
            )
