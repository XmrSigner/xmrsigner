from ots.address import Address
from ots.seed import SeedIndices

from re import search, IGNORECASE
from numpy import array as NumpyArray
from datetime import date
from logging import getLogger
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol
from xmrsigner.urtypes.xmr import (
    XmrOutput,
    XmrTxUnsigned
)
from xmrsigner.helpers.ur2.ur_decoder import URDecoder
from xmrsigner.models.base_decoder import (
    DecodeQRStatus,
    BaseQrDecoder
)
from xmrsigner.models.seed_decoder import (
    SeedQrDecoder,
    MnemonicQrDecoder
)
from xmrsigner.models.monero_decoder import (
    MoneroWalletQrDecoder,
    MoneroAddressQrDecoder
)
from xmrsigner.models.date_decoder import DateQrDecoder
from xmrsigner.models.timestamp_decoder import TimestampQrDecoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.settings_definition import Language


logger = getLogger(__name__)


class DecodeQR:
    """
    Used to process images or string data from animated qr codes.
    """

    def __init__(self):
        self.complete: bool = False
        self.qr_type: QrType|None = None
        self.decoder: BaseQrDecoder|None = None

    def add_image(self, image: NumpyArray) -> DecodeQRStatus|None:
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        print(f'data: {data} ({type(data)}({len(data) if data else 0}))')
        if data == None:
            return DecodeQRStatus.FALSE
        return self.add_data(data)

    def decoder_for_type(cls, qr_type: QrType) -> BaseQrDecoder|None:
        if qr_type in [
            QrType.XMR_OUTPUT_UR,
            QrType.XMR_TX_UNSIGNED_UR
            ]:
            return URDecoder()  # BCUR Decoder
        if qr_type in [
                QrType.SEED_QR,
                QrType.COMPACT_SEED_QR
                ]:
            return SeedQrDecoder()
        if qr_type == QrType.MNEMONIC:
            return MnemonicQrDecoder()
        if qr_type == QrType.SETTINGS:
            return SettingsQrDecoder()  # Settings config
        if qr_type == QrType.MONERO_ADDRESS:
            return MoneroAddressQrDecoder() # Single Segment monero address
        if qr_type == QrType.MONERO_WALLET:
            return MoneroWalletQrDecoder() # Single Segment monero wallet
        if qr_type == QrType.DATE:
            return DateQrDecoder()
        if qr_type == QrType.TIMESTAMP:
            return TimestampQrDecoder()

    def add_data(self, data: str|bytes|None) -> DecodeQRStatus:
        if data == None:
            return DecodeQRStatus.FALSE
        qr_type: QrType|None = DecodeQR.detect_segment_type(data)
        print(f'qr type: {qr_type}')
        if self.qr_type == None:
            self.qr_type = qr_type
            self.decoder = self.decoder_for_type(qr_type)
        elif self.qr_type != qr_type:
            raise Exception('QR Fragment Unexpected Type Change')
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
                QrType.BYTES_UR
            ]:
            self.decoder.receive_part(qr_str)
            if self.decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            return DecodeQRStatus.PART_COMPLETE # segment added to ur2 decoder
        # All other formats use the same method signature
        rt = self.decoder.add(qr_str, self.qr_type)
        if rt == DecodeQRStatus.COMPLETE:
            self.complete = True
        return rt

    def get_output(self) -> bytes|None:
        if self.complete and  self.qr_type == QrType.XMR_OUTPUT_UR:
            cbor = self.decoder.result_message().cbor
            return XmrOutput.from_cbor(cbor).data

    def get_tx(self) -> bytes|None:
        if self.complete and self.qr_type == QrType.XMR_TX_UNSIGNED_UR:
            cbor = self.decoder.result_message().cbor
            print(XmrTxUnsigned)
            return XmrTxUnsigned.from_cbor(cbor).data

    def get_seed_phrase(self) -> list[str]|None:
        if self.is_mnemonic:
            return self.decoder.seed_phrase
        if self.is_wallet:
            return self.decoder.seed_phrase

    def get_seed_indices(self) -> SeedIndices|None:
        if self.is_seed:
            return self.decoder.seed_indices

    def get_date(self) -> date|None:
        if self.is_date or self.is_timestamp:
            return self.decoder.date

    def get_settings_data(self) -> str|None:
        if self.is_settings:
            return self.decoder.data

    def get_address(self) -> Address|None:
        if self.is_address or self.is_wallet:
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
    def is_outputs(self) -> bool:
        return self.qr_type == QrType.XMR_OUTPUT_UR

    @property
    def is_tx_unsigned(self) -> bool:
        return self.qr_type == QrType.XMR_TX_UNSIGNED_UR

    @property
    def is_seed(self) -> bool:
        print(f'DecodeQR.is_seed(): qr_type: {self.qr_type}')
        return self.qr_type in [
            QrType.SEED_QR,
            QrType.COMPACT_SEED_QR
        ]

    @property
    def is_mnemonic(self) -> bool:
        print(f'DecodeQR.is_seed(): qr_type: {self.qr_type}')
        return self.qr_type == QrType.MNEMONIC

    @property
    def is_wallet(self) -> bool:
        print(f'DecodeQR.is_seed(): qr_type: {self.qr_type}')
        return self.qr_type == QrType.MONERO_WALLET

    @property
    def is_view_only_wallet(self) -> bool:
        return self.is_wallet and self.decoder.is_view_only

    @property
    def is_json(self) -> bool:
        return self.qr_type in [QrType.SETTINGS, QrType.JSON]

    @property
    def is_address(self) -> bool:
        return self.qr_type == QrType.MONERO_ADDRESS

    @property
    def is_settings(self) -> bool:
        return self.qr_type == QrType.SETTINGS

    @property
    def is_timestamp(self) -> bool:
        return self.qr_type == QrType.TIMESTAMP

    @property
    def is_date(self) -> bool:
        return self.qr_type == QrType.DATE

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
    def detect_segment_type(segment: bytes|str):
        # print("-------------- DecodeQR.detect_segment_type --------------")
        # print(type(s))
        # print(len(s))
        try:
            s: str = segment if type(segment) == str else segment.decode()

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
            # date
            if search(r'^date:\d{4}-\d{2}-\d{2}$', s):
                return QrType.DATE
            # timestamp
            if search(r'^timestamp:\d+$', s):
                return QrType.TIMESTAMP
            # Monero Address
            if MoneroAddressQrDecoder.is_monero_address(s):
                return QrType.MONERO_ADDRESS
            # config data
            if s.startswith("settings::"):
                return QrType.SETTINGS
            # Seed phrase
            # if the stripped string splitted has 12, 13, 16, 24 or 25 elements we assume it's a mnemonic
            if len(s.strip().split()) in (12, 13, 16, 24, 25):
                return QrType.MNEMONIC
        except UnicodeDecodeError:
            # Probably this isn't meant to be string data; check if it's valid byte data
            # below.
            pass
        print(f'byte({len(segment)})<{type(segment)}>? {segment}')
        # 33 bytes for 24-word CompactSeedQR; 17 bytes for 12-word CompactSeedQR, 22 for polyseed
        if isinstance(segment, bytes) and len(segment) in (33, 17, 22):
            return QrType.COMPACT_SEED_QR
        return QrType.INVALID
