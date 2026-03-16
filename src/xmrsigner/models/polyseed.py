from xmrsigner.models.seed import Seed, InvalidSeedException, SeedType
from xmrsigner.models.settings_definition import SettingsConstants
from xmrsigner.helpers.monero_time import MoneroTime
from xmrsigner.helpers.network import Network
from monero.const import NET_MAIN
from polyseed import Polyseed
from polyseed.lang import Language
from polyseed.exceptions import PolyseedWordCountMissmatchException, PolyseedLanguageNotFoundException
from monero.seed import Seed as MoneroSeed

from unicodedata import normalize

from binascii import hexlify
from typing import List, Optional

class PolyseedSeed(Seed):

    def __init__(self,
                 mnemonic: List[str] = None,
                 passphrase: str = "",
                 wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH,
                 network: str = NET_MAIN):
        self.wordlist_language_code: str = wordlist_language_code
        self.prefered_language: str = wordlist_language_code
        self.network: str = network
        self.height: int = 0

        if not mnemonic:
            raise Exception("Must initialize a Seed with a mnemonic List[str]")
        self._mnemonic: List[str] = normalize("NFKD", " ".join(mnemonic).strip()).split()

        self._passphrase: str = ''
        self.set_passphrase(passphrase, regenerate_seed=False)

        self.seed_bytes: bytes = None
        self.address: Optional[str] = None
        self._generate_seed()

    @property
    def type(self) -> SeedType:
        return SeedType.Polyseed

    @staticmethod
    def get_wordlist(wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> List[str]:
        if wordlist_language_code == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH:
            return Language.get_lang_by_code(wordlist_language_code).words
        else:
            try:
                return Language.get_lang_by_code(wordlist_language_code).words
            except PolyseedLanguageNotFoundException:
                pass
        raise Exception(f"Unrecognized wordlist_language_code {wordlist_language_code}")

    def _generate_seed(self) -> bool:
        try:
            ps: Polyseed = None
            try:
                ps = Polyseed.decode(self.mnemonic_str)
            except PolyseedLanguageNotFoundException:
                ps = Polyseed.decode_explicit(self.mnemonic_str, self.prefered_language)
            if ps.is_encrypted():
                if not self.passphrase:
                    raise Exception('No passphrase provided for encrypted polyseed')
            if self.passphrase:
                ps.crypt(self.passphrase)
            self.seed_bytes = ps.keygen()
            self.address = str(MoneroSeed(hexlify(self.seed_bytes).decode()).public_address(self.network))
            self.height = MoneroTime(str(Network.ensure(self.network))).getBlockchainHeight(ps.get_birthday())
        except Exception as e:
            raise InvalidSeedException(repr(e))

    def to_monero_seed(self, password: Optional[str]) -> Seed:
        return Seed.from_key(hexlify(self.seed_bytes), password, self.wordlist_language_code, self.height, self.network)

    ### override operators
    def __eq__(self, other: Seed):
        if isinstance(other, Seed):
            return self.seed_bytes == other.seed_bytes
        return False
