import unicodedata

from monero.seed import Seed as MoneroSeed
from monero.seed import wordlists as MoneroWordlists
from monero.wallet import Wallet
from monero.backends.offline import OfflineWallet
from typing import List, Optional, Union
from hashlib import sha256
from binascii import unhexlify, hexlify

from xmrsigner.models.settings import SettingsConstants



class InvalidSeedException(Exception):
    pass


class NoSeedBytesException(Exception):
    pass

class Seed:

    def __init__(self,
                 mnemonic: List[str] = None,
                 passphrase: Optional[str] = None,
                 wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH):
        self.wordlist_language_code = wordlist_language_code

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        mnemonic_words = len(mnemonic)
        if mnemonic_words not in (12, 13, 24, 25):
            raise Exception(f'Mnemonic has not the right amounts of words, expected to have 12, 13, 24 or 25. Got: {mnemonic_words}')
        self._mnemonic: List[str] = unicodedata.normalize('NFKD', ' '.join(mnemonic).strip()).split()

        self._passphrase: Optional[str] = None
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
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
            self.seed_bytes = unhexlify(MoneroSeed(self.mnemonic_str, SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES[self.wordlist_language_code]).hex)
        except Exception as e:
            raise InvalidSeedException(repr(e))

    @property
    def mnemonic_str(self) -> str:
        return " ".join(self._mnemonic)

    @property
    def mnemonic_list(self) -> List[str]:
        return self._mnemonic

    @property
    def mnemonic_display_str(self) -> str:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic))
    
    @property
    def mnemonic_display_list(self) -> List[str]:
        return unicodedata.normalize("NFC", " ".join(self._mnemonic)).split()

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
        return unicodedata.normalize("NFC", self._passphrase)

    @property
    def has_passphrase(self) -> bool:
        return self._passphrase is not None and self._passphrase is not ''

    def set_passphrase(self, passphrase: Optional[str] = None, regenerate_seed: bool = True):
        if passphrase and passphrase != '':
            self._passphrase = unicodedata.normalize("NFKD", passphrase)
        else:
            self._passphrase = None

        if regenerate_seed:
            # Regenerate the internal seed since passphrase changes the result
            self._generate_seed()

    @property
    def is_my_monero(self) -> bool:
        return len(self._mnemonic) == 13

    @property
    def wordlist(self) -> List[str]:
        return self.get_wordlist(self.wordlist_language_code)

    def set_wordlist_language_code(self, language_code: str) -> None:
        if language_code in SettingsConstants.ALL_WORDLIST_LANGUAGE_ENGLISH__NAMES:
            self.wordlist_language_code = language_code
            return
        raise Exception(f"Unrecognized wordlist_language_code {language_code}")

    def get_fingerprint(self, network: str = SettingsConstants.MAINNET) -> str:
        return sha256(network.encode() + self.seed_bytes).hexdigest()[-6:].upper()

    def get_wallet(self) -> Wallet:
        if self.seed_bytes is None:
            raise NoSeedBytesException()
        monero_seed = MoneroSeed(hexlify(self.seed_bytes).decode())
        return Wallet(OfflineWallet(monero_seed.public_address(), monero_seed.secret_view_key(), monero_seed.secret_spend_key()))
    
    @classmethod
    def from_key(cls, key: Union[str, bytes], password: Union[str, bytes, None] = None, language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> 'Seed':
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
                language_code
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