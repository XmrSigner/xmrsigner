from ots.enums import AddressType, Network
from ots.address import Address, AddressString
from ots.seed import (
    MoneroSeed,
    Polyseed,
    LegacySeed,
    Seed,
    SeedLanguage
)

from urllib.parse import urlparse, parse_qs
from re import search

from xmrsigner.models.base_decoder import BaseSingleFrameQrDecoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.base_decoder import DecodeQRStatus


class MoneroAddressQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a monero address
    """

    def __init__(self):
        super().__init__()
        self.address: Address|None = None

    def add(
        self,
        segment: str,
        qr_type=QrType.MONERO_ADDRESS
    ) -> DecodeQRStatus:
        r = search(r'\b[1-9A-HJ-NP-Za-km-z]{95}\b|[1-9A-HJ-NP-Za-km-z]{106}', segment)
        if r != None:
            try:
                self.address = Address.fromString(r.group(0))
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except:
                pass
        return DecodeQRStatus.INVALID

    @staticmethod
    def is_monero_address(s: str) -> bool:
        try:
            Address.fromString(s[7:] if s.startswith('monero:') else s)
            return True
        except:
            return False


class MoneroWalletQrDecoder(BaseSingleFrameQrDecoder):
    """
    Decodes single frame representing a monero wallet
    """

    def __init__(self):
        super().__init__()
        self.address: Address|None = None
        self.view_key: str|None = None
        self.spend_key: str|None = None
        self.height: int = 0

    def parse_monero_wallet_uri(
        self,
        uri: str
    ) -> tuple[str, str, str, str]:
        ''' returns address, view_key, spend_key, height '''
        parsed_uri = urlparse(uri)
        query_params = parse_qs(parsed_uri.query)
        if 'view_key' in query_params or 'spend_key' in query_params:
            address = parsed_uri.path.split(':')[-1]
            view_key = query_params.get('view_key', [''])[0]
            spend_key = query_params.get('spend_key', [''])[0]
            height = query_params.get('height', [''])[0]
            return address, view_key, spend_key, height
        mnemonic_seed: str|None = None
        if 'mnemonic_seed' in query_params:
            mnemonic_seed = query_params.get('mnemonic_seed', [''])[0]
        elif 'seed' in query_params:
            mnemonic_seed = query_params.get('seed', [''])[0]
        if mnemonic_seed is None or mnemonic_seed == '':
            raise Exception('No valid mnemonic!')
        seed: Seed = decode_mnemonic(mnemonic_seed)
        address = seed.address
        view_key = seed.wallet.secretViewKey().insecure()
        spend_key = seed.wallet.secretSpendKey().insecure()
        height = query_params.get('height', [''])[0]
        return address, view_key, spend_key, height

    def decode_mnemonic(
        self,
        mnemonic: str,
        network: Network = Network.MAIN,
        password: str = '',
        passphrase: str = '',
    ) -> Seed:
        word_count: int = len(mnemonic.split())
        if word_count in (24, 25):
            return MoneroSeed.decode(
                mnemonic,
                network=network,
                passphrase=passphrase
            )
        if word_count == 16:
            return Polyseed.decode(
                mnemonic,
                network=network,
                password=password,
                passphrase=passphrase
            )
        if word_count in (12, 13):
            return LegacySeed.decode(
                mnemonic,
                network=network
            )
        raise Exception(f'Not a valid mnemonic, a mnemonic with {word_count} words does not exist!')

    def add(
        self,
        segment,
        qr_type=QrType.MONERO_WALLET
    ) -> DecodeQRStatus:
        address, view_key, spend_key, height = self.parse_monero_wallet_uri(segment)
        if address != None:
            try:
                self.address = Address.fromString(address)
                self.view_key = view_key if view_key != '' else None
                self.spend_key = spend_key if spend_key != '' else None
                self.height = int(height if height != '' else 0)
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except:
                pass
        return DecodeQRStatus.INVALID

    @property
    def seed(self) -> Seed|None:
        if not self.is_view_only:
            return MoneroSeed.create(
                bytes.fromhex(self.spend_key),
                height=self.height,
                network=self.address.network
            )

    @property
    def seed_phrase(self) -> list[str]|None:
        s = self.seed
        if s:
            return s.phrase(SeedLanguage.fromCode('en')).insecure().split()

    @property
    def is_valid(self):
        return self.address is not None and self.view_key is not None

    @property
    def is_view_only(self):
        return self.spend_key is None

    @property
    def has_height(self):
        return self.height != 0

    def get_data(self) -> dict[str, str|int]:
        return {
            'address': self.address.base58 if self.address is not None else '',
            'view_key': self.view_key,
            'spend_key': self.spend_key,
            'height': self.height
        }
