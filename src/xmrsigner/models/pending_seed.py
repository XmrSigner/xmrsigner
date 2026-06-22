from ots.enums import (
    Network,
    SeedType
)
from ots.seed import (
    Seed,
    MoneroSeed,
    LegacySeed,
    Polyseed,
    SeedIndices
)
from ots.ots import Ots


class PendingSeed:

    def __init__(
        self,
        type: SeedType|None = None,
        network: Network|None = None,
        password: str|None = None,  # key encryption password for Polyseed
        passphrase: str|None = None,  # offset passphrase for MoneroSeed and Polyseed, LegacySeed is not supported
        height: int|None = None,
        isLegacy: bool|None = None,
        pre_filled: bool = False
    ):
        self.type: SeedType = type or SeedType.MONERO
        self.network: Network = network or Network.MAIN
        self.password: str = password or ''
        self.passphrase: str = passphrase or ''
        self.height: int|None = height
        self.isLegacy: bool = isLegacy or False
        self.pre_filled = pre_filled

    @property
    def length_expected(self) -> int:
        if self.type == SeedType.MONERO:
            return 13 if self.isLegacy else 25
        return 16

    @property
    def length(self) -> int:
        raise NotImplementedError('Need to override method')

    @property
    def missing(self) -> int:
        raise NotImplementedError('Need to override method')

    @property
    def first_missing_index(self) -> int|None:
        raise NotImplementedError('Need to override method')

    @property
    def complete(self) -> bool:
        return self.missing == 0

    def clear(self) -> None:
        raise NotImplementedError('Need to override method')

    def seed(self) -> Seed:
        raise NotImplementedError('Need to override method')


class PendingSeedPhrase(PendingSeed):

    def __init__(
        self,
        mnemonic: list[str]|None = None,
        type: SeedType|None = None,
        network: Network|None = None,
        password: str|None = None,  # key encryption password for Polyseed
        passphrase: str|None = None,  # offset passphrase for MoneroSeed and Polyseed, LegacySeed is not supported
        height: int|None = None,
        isLegacy: bool|None = None,
        pre_filled: bool = False
    ):
        super().__init__(
            type,
            network,
            password,
            passphrase,
            height,
            isLegacy,
            pre_filled
        )
        self._mnemonic: list[str|None] = mnemonic or []
        self._mnemonic += [None] * (self.length_expected - self.length)

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
        return self._mnemonic[index] or ''

    def seed(
        self,
        without_checksum: bool = False
    ) -> Seed:
        print(f'''
mnemonic: {' '.join(self._mnemonic if not without_checksum else self._mnemonic[:-2])}
length: {self.length}
missing: {self.missing}
type: {self.type}
        ''')
        if (
            (self.missing > 0
             and not (
                 without_checksum
                 and self.type == SeedType.MONERO
                 )
             )
            or (self.missing > 1
                and not without_checksum
                and self.type == SeedType.MONERO
            )
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
                height=self.height or 0
            )
        return MoneroSeed.decode(
                self.mnemonic if not without_checksum else self.mnemonic_without_checksum,
                network=self.network,
                height=self.height or 0,
                passphrase=self.passphrase
            )

    def __str__(self) -> str:
        return f"{self.type}: {' '.join([w if w is not None else '*' for w in self._mnemonic])}"


class PendingSeedIndices(PendingSeed):

    def __init__(
        self,
        indices: list[int]|SeedIndices|None = None,
        type: SeedType|None = None,
        network: Network|None = None,
        password: str|None = None,  # key encryption password for Polyseed
        passphrase: str|None = None,  # offset passphrase for MoneroSeed and Polyseed, LegacySeed is not supported
        height: int|None = None,
        isLegacy: bool|None = None,
        pre_filled: bool = False
    ):
        super().__init__(
            type,
            network,
            password,
            passphrase,
            height,
            isLegacy,
            pre_filled
        )
        self._indices: list[int|None] = indices.values if isinstance(indices, SeedIndices) else indices or []
        self._indices += [None] * (self.length_expected - self.length)

    @property
    def length(self) -> int:
        return len(self._indices)

    @property
    def missing(self) -> int:
        return sum([1 if v is None else 0 for v in self._indices])

    @property
    def first_missing_index(self) -> int|None:
        try:
            return self._indices.index(None)
        except:
            return None

    def clear(self) -> None:
        self._indices.clear()
        self._indices += [None] * self.length_expected

    def set(self, value: str, index: int) -> None:
        self._indices[index] = value

    def get(self, index: int) -> int:
        return self._indices[index] or -1

    def seed(self) -> Seed:
        print(f'''
indices: {', '.join(str(v) for v in self._indices)}
length: {self.length}
missing: {self.missing}
type: {self.type}
        ''')
        if self.missing > 0:
            raise Exception('Missing words in mnemonic')
        if self.type == SeedType.POLYSEED:
            return Polyseed.decodeIndices(
                SeedIndices.fromValues(self._indices),
                network=self.network,
                password=self.password,
                passphrase=self.passphrase
            )
        if self.isLegacy:
            return LegacySeed.decodeIndices(
                SeedIndices.fromValues(self._indices),
                network=self.network,
                height=self.height or 0
            )
        return MoneroSeed.decode(
                SeedIndices.fromValues(self._indices),
                network=self.network,
                height=self.height or 0,
                passphrase=self.passphrase
            )

    def __str__(self) -> str:
        return f"{self.type}: {', '.join([str(v) if v is not None else '*' for v in self._indices])}"


class PendingSeedEntropy(PendingSeed):

    def __init__(
        self,
        entropy: bytes|None = None,
        type: SeedType|None = None,
        network: Network|None = None,
        password: str|None = None,  # key encryption password for Polyseed
        passphrase: str|None = None,  # offset passphrase for MoneroSeed and Polyseed, LegacySeed is not supported
        height: int|None = None,
        isLegacy: bool|None = None
    ):
        super().__init__(
            type,
            network,
            password,
            passphrase,
            height,
            isLegacy,
            True
        )
        self.entropy: bytes|None = entropy

    @property
    def length(self) -> int:
        return self.length_expected if self.entropy is not None else 0

    @property
    def missing(self) -> int:
        return self.length_expected - self.length

    @property
    def first_missing_index(self) -> int|None:
        return 0 if self.missing else None

    def clear(self) -> None:
        self.entropy = None

    def seed(self) -> Seed:
        if self.missing:
            raise Exception('Entropy not set to create seed.')
        if self.type == SeedType.POLYSEED:
            return Polyseed.create(
                self.entropy[:19],
                network=self.network,
                time=Ots.timestampFromHeight(self.height),
                passphrase=self.passphrase
            )
        if not self.isLegacy:
            return MoneroSeed.create(
                self.entropy,
                height=self.height,
                network=self.network
            )
        raise Exception('Crreating legacy seeds are not supported.')
