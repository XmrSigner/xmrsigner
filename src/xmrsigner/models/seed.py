from unicodedata import normalize
from enum import Enum
from monero.seed import Seed as MoneroSeed
from monero.seed import wordlists as MoneroWordlists
from monero.wallet import Wallet
from monero.backends.offline import OfflineWallet
from monero.const import NET_MAIN
from typing import List, Optional, Union
from hashlib import sha256
from binascii import unhexlify, hexlify

from xmrsigner.models.settings_definition import SettingsConstants


class SeedType(Enum):
    Monero = 1
    MyMonero = 2
    Polyseed = 3


class InvalidSeedException(Exception):
    pass


class NoSeedBytesException(Exception):
    pass

class Seed:

    def __init__(self,
                 mnemonic: List[str] = None,
                 passphrase: Optional[str] = None,
                 wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH,
                 height: int = 0,
                 network: str = NET_MAIN):
        self.wordlist_language_code = wordlist_language_code

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        mnemonic_words = len(mnemonic)
        if mnemonic_words not in (12, 13, 24, 25):
            raise Exception(f'Mnemonic has not the right amounts of words, expected to have 12, 13, 24 or 25. Got: {mnemonic_words}')
        self._mnemonic: List[str] = normalize('NFKD', ' '.join(mnemonic).strip()).split()

        self._passphrase: Optional[str] = None
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
        self.address: Optional[str] = None
        self.network: str = network
        self.height = height
        self._generate_seed()

    @staticmethod
    def get_wordlist(wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> List[str]:
        if wordlist_language_code == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH:
            if wordlist_language_code in SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES:
                return MoneroWordlists.get_wordlist(SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES[wordlist_language_code]).word_list
        raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")

    def _generate_seed(self) -> None:
        if self.passphrase is not None:
            raise Exception('Passwords for monero seeds are not yet implemented')
        try:
            monero_seed = MoneroSeed(self.mnemonic_str, SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES[self.wordlist_language_code])
            self.seed_bytes = unhexlify(monero_seed.hex)
            self.address = str(monero_seed.public_address(self.network))
        except Exception as e:
            raise InvalidSeedException(repr(e))

    def change_network(self, network: str) -> None:
        self.network = network
        self._generate_seed

    @property
    def mnemonic_str(self) -> str:
        return " ".join(self._mnemonic)

    @property
    def mnemonic_list(self) -> List[str]:
        return self._mnemonic

    @property
    def mnemonic_display_str(self) -> str:
        return normalize("NFC", " ".join(self._mnemonic))

    @property
    def mnemonic_display_list(self) -> List[str]:
        return normalize("NFC", " ".join(self._mnemonic)).split()

    @property
    def passphrase(self) -> Optional[str]:
        return self._passphrase

    @property
    def passphrase_str(self) -> str:
        return self._passphrase or ''

    @property
    def passphrase_display(self):
        if not self._passphrase:
            return ''
        return normalize("NFC", self._passphrase)

    @property
    def has_passphrase(self) -> bool:
        return self._passphrase is not None and self._passphrase != ''

    def set_passphrase(self, passphrase: Optional[str] = None, regenerate_seed: bool = True):
        if passphrase and passphrase != '':
            self._passphrase = normalize("NFKD", passphrase)
        else:
            self._passphrase = None

        if regenerate_seed:
            # Regenerate the internal seed since passphrase changes the result
            self._generate_seed()

    @property
    def is_my_monero(self) -> bool:
        return len(self._mnemonic) == 13

    @property
    def type(self) -> SeedType:
        return SeedType.Monero if not self.is_my_monero else SeedType.MyMonero

    @property
    def wordlist(self) -> List[str]:
        return self.get_wordlist(self.wordlist_language_code)

    @property
    def monero_seed(self) -> MoneroSeed:
        return MoneroSeed(hexlify(self.seed_bytes).decode())

    @property
    def wallet(self) -> Wallet:
        if self.seed_bytes is None:
            raise NoSeedBytesException()
        monero_seed = self.monero_seed
        return Wallet(OfflineWallet(monero_seed.public_address(self.network), monero_seed.secret_view_key(), monero_seed.secret_spend_key()))

    @property
    def fingerprint(self) -> str:
        return sha256(self.address.encode()).hexdigest()[-6:].upper() if self.address else ''

    def set_wordlist_language_code(self, language_code: str) -> None:
        if language_code in SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES:
            self.wordlist_language_code = language_code
            return
        raise Exception(f"Unrecognized wordlist_language_code {language_code}")

    @classmethod
    def from_key(cls, key: Union[str, bytes], password: Union[str, bytes, None] = None, language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH, height: int = 0, network: str = NET_MAIN) -> 'Seed':
        if password is not None:
            raise Exception('Passwords for monero seeds are not yet implemented')
        if type(key) == bytes:
            key = key.decode()
        if language_code in SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES:
            return cls(
                MoneroSeed(
                    key,
                    SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES[language_code]
                ).phrase.split(' '),
                password,
                language_code,
                height,
                network
            )
        raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")

    ### override operators
    def __eq__(self, other):
        if isinstance(other, Seed):
            return self.seed_bytes == other.seed_bytes
        return False

    def __repr__(self) -> str:
        out =  f'type:     {self.__class__.__name__}\n'
        out += f'phrase:   {self.mnemonic_str or "None"}\n'
        out += f'language: {self.wordlist_language_code}\n'
        out += f'password: {self.passphrase or "None"}\n'
        return out
