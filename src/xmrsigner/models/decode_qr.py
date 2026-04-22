from ots.address import Address

from re import search, IGNORECASE
from numpy import array as NumpyArray
from logging import getLogger
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
from xmrsigner.urtypes.xmr import (
    XmrOutput,
    XmrTxUnsigned
)
from xmrsigner.helpers.ur2.ur_decoder import URDecoder
from xmrsigner.models.base_decoder import DecodeQRStatus
from xmrsigner.models.seed_decoder import SeedQrDecoder
from xmrsigner.models.monero_decoder import MoneroWalletQrDecoder, MoneroAddressQrDecoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.settings_definition import Language


logger = getLogger(__name__)


class DecodeQR:
    """
    Used to process images or string data from animated qr codes.
    """

    def __init__(self, wordlist_language: Language = Language.ENGLISH):
        self.wordlist_language = wordlist_language
        self.complete = False
        self.qr_type = None
        self.decoder = None

    def add_image(self, image):
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        if data == None:
            return DecodeQRStatus.FALSE
        return self.add_data(data)

    def add_data(self, data) -> DecodeQRStatus:
        if data == None:
            return DecodeQRStatus.FALSE

        qr_type = DecodeQR.detect_segment_type(data, wordlist_language=self.wordlist_language)
        print(f'qr type: {qr_type}')

        if self.qr_type == None:
            self.qr_type = qr_type
            print(f'self.qr_type: {self.qr_type}')
            if self.qr_type in [
                QrType.XMR_OUTPUT_UR,
                QrType.XMR_TX_UNSIGNED_UR
                ]:
                print('UR')
                self.decoder = URDecoder()  # BCUR Decoder
            elif self.qr_type in [
                    QrType.SEED_QR,
                    QrType.COMPACT_SEED_QR,
                    QrType.MNEMONIC
                    ]:
                self.decoder = SeedQrDecoder(wordlist_language=self.wordlist_language)
            elif self.qr_type == QrType.SETTINGS:
                self.decoder = SettingsQrDecoder()  # Settings config
            elif self.qr_type == QrType.MONERO_ADDRESS:
                self.decoder = MoneroAddressQrDecoder() # Single Segment monero address
            elif self.qr_type == QrType.MONERO_WALLET:
                self.decoder = MoneroWalletQrDecoder() # Single Segment monero wallet
        elif self.qr_type != qr_type:
            raise Exception('QR Fragment Unexpected Type Change')
        print(f'decoder: {str(self.decoder)}')
        if not self.decoder:
            # Did not find any recognizable format
            return DecodeQRStatus.INVALID
        # Process the binary formats first
        if self.qr_type == QrType.COMPACT_SEED_QR:
            rt = self.decoder.add(data, QrType.COMPACT_SEED_QR)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt
        # Convert to string data
        # Should always be bytes, but the test suite has some manual datasets that
        # are strings.
        qr_str = data.decode() if type(data) == bytes else data
        if self.qr_type == QrType.SEED_QR:
            rt = self.decoder.add(data, QrType.SEED_QR)
            print(f'rt: {rt}')
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt
        if self.qr_type in [
                QrType.XMR_OUTPUT_UR,
                QrType.XMR_KEYIMAGE_UR,
                QrType.XMR_TX_UNSIGNED_UR,
                QrType.XMR_TX_SIGNED_UR,
                QrType.BYTES__UR
                ]:
            self.decoder.receive_part(qr_str)
            if self.decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # segment added to ur2 decoder
        else:
            # All other formats use the same method signature
            rt = self.decoder.add(qr_str, self.qr_type)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

    def get_output(self):
        if self.complete and  self.qr_type == QrType.XMR_OUTPUT_UR:
            cbor = self.decoder.result_message().cbor
            return XmrOutput.from_cbor(cbor).data
        return None

    def get_tx(self):
        if self.complete and self.qr_type == QrType.XMR_TX_UNSIGNED_UR:
            cbor = self.decoder.result_message().cbor
            print(XmrTxUnsigned)
            return XmrTxUnsigned.from_cbor(cbor).data
        return None

    def get_seed_phrase(self):
        if self.is_seed:
            return self.decoder.get_seed_phrase()
        if self.is_wallet:
            return self.decoder.seed

    def get_settings_data(self):
        if self.is_settings:
            return self.decoder.data

    def get_address(self) -> Address|None:
        if self.is_address:
            return self.decoder.address

    def get_qr_data(self) -> dict:
        """
        This provides a single access point for external code to retrieve the QR data,
        regardless of which decoder is actually instantiated.
        """
        return self.decoder.get_qr_data()

    def get_percent_complete(self) -> int:
        if not self.decoder:
            return 0
        if self.qr_type in [
                QrType.XMR_OUTPUT_UR,
                QrType.XMR_TX_UNSIGNED_UR
                ]:
            return int(self.decoder.estimated_percent_complete() * 100)
        if self.decoder.total_segments == 1:
            # The single frame QR formats are all or nothing
            return 100 if self.decoder.complete else 0
        return 0

    @property
    def is_complete(self) -> bool:
        return self.complete

    @property
    def is_invalid(self) -> bool:
        return self.qr_type == QrType.INVALID

    @property
    def is_ur(self) -> bool:
        return self.qr_type in [
            QrType.XMR_OUTPUT_UR,
            QrType.XMR_TX_UNSIGNED_UR
        ]

    @property
    def is_seed(self):
        print(f'DecodeQR.is_seed(): qr_type: {self.qr_type}')
        return self.qr_type in [
            QrType.SEED_QR,
            QrType.COMPACT_SEED_QR,
            QrType.MNEMONIC
        ]

    @property
    def is_wallet(self):
        print(f'DecodeQR.is_seed(): qr_type: {self.qr_type}')
        return self.qr_type == QrType.MONERO_WALLET

    @property
    def is_view_only_wallet(self):
        return self.is_wallet and self.decoder.is_view_only

    @property
    def is_json(self):
        return self.qr_type in [QrType.SETTINGS, QrType.JSON]

    @property
    def is_address(self):
        return self.qr_type == QrType.MONERO_ADDRESS

    @property
    def is_settings(self):
        return self.qr_type == QrType.SETTINGS

    @staticmethod
    def extract_qr_data(image: NumpyArray, is_binary:bool = False) -> str:
        if image is None:
            return None
        barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE], binary=is_binary)
        # if barcodes:
            # print("--------------- extract_qr_data ---------------")
            # print(barcodes)
        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data

    @staticmethod
    def detect_segment_type(segment: bytes|str, wordlist_language: Language|None = None):
        # print("-------------- DecodeQR.detect_segment_type --------------")
        # print(type(s))
        # print(len(s))
        try:
            s = segment if type(segment) == str else segment.decode()

            UR_XMR_OUTPUT = 'xmr-output'
            UR_XMR_KEY_IMAGE = 'xmr-keyimage'
            UR_XMR_TX_UNSIGNED = 'xmr-txunsigned'
            UR_XMR_TX_SIGNED = 'xmr-txsigned'
            # XMR UR
            if search(f"^UR:{UR_XMR_OUTPUT}/", s, IGNORECASE):
                return QrType.XMR_OUTPUT_UR
            if search(f'^UR:{UR_XMR_KEY_IMAGE}/', s, IGNORECASE):
                return QrType.XMR_KEYIMAGE_UR
            if search(f'^UR:{UR_XMR_TX_UNSIGNED}/', s, IGNORECASE):
                return QrType.XMR_TX_UNSIGNED_UR
            if search(f'^UR:{UR_XMR_TX_SIGNED}/', s, IGNORECASE):
                return QrType.XMR_TX_SIGNED_UR
            if s.startswith('monero_wallet:'):
                return QrType.MONERO_WALLET
            # Seed
            print(f'search: ({len(s)}){s}')
            if (decimals := search(r'(\d{52,100})', s)) and len(decimals.group(1)) in (52, 64, 100):
                return QrType.SEED_QR
            # Monero Address
            if MoneroAddressQrDecoder.is_monero_address(s):
                return QrType.MONERO_ADDRESS
            # config data
            if s.startswith("settings::"):
                return QrType.SETTINGS
            # Seed
            # if the stripped string splitted has 12, 13, 16, 24 or 25 elements we assume it's a mnemonic
            if len(s.strip().split()) in (12, 13, 16, 24, 25):
                return QrType.MNEMONIC
        except UnicodeDecodeError:
            # Probably this isn't meant to be string data; check if it's valid byte data
            # below.
            pass
        # TODO: 2024-08-26, check and write tests
        print(f'byte({len(s)})<{type(s)}>? {s}')
        # Is it byte data?
        # 32 bytes for 24-word CompactSeedQR; 16 bytes for 12-word CompactSeedQR, 22 for polyseed
        if len(s) in (33, 17, 22):  # TODO: or comment or statement wrong!
            try:
                bitstream = ''
                for b in s:
                    bitstream += bin(b).lstrip('0b').zfill(8)
                return QrType.COMPACT_SEED_QR
            except Exception as e:
                # Couldn't extract byte data; assume it's not a byte format
                print(f'exception: {e}')
        return QrType.INVALID
