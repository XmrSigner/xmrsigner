from ots.seed import Seed
from ots.address import Address

from xmrsigner.models.base_encoder import BaseStaticQrEncoder
from xmrsigner.models.ur_encoder import UrQrEncoder
from xmrsigner.urtypes.xmr import (
    XmrTxSigned,
    XMR_TX_SIGNED,
    XmrKeyImage,
    XMR_KEY_IMAGE
)
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.settings_definition import QrDensity


class MoneroAddressEncoder(BaseStaticQrEncoder):

    def __init__(self, address: str|Address):
        super().__init__()
        self.address: str = address if type(address) == str else address.base58

    def next_part(self):
        return f'monero:{self.address}'

    def get_qr_type(self):
        return QrType.MONERO_ADDRESS


class ViewOnlyWalletQrEncoder(BaseStaticQrEncoder):

    def __init__(self, seed: Seed):
        super().__init__()
        self.height: int = seed.height
        self.address: str = seed.address.base58
        self.secret_view_key: str = seed.wallet.secretViewKey().insecure()

    def next_part(self):
        return f'monero_wallet:{self.address}?view_key={self.secret_view_key}&height={self.height}'

    def get_qr_type(self):
        return QrType.WALLET_VIEW_ONLY


class ViewOnlyWalletJsonQrEncoder(ViewOnlyWalletQrEncoder):

    def next_part(self):
        return f'{{"primaryAddress": "{self.address}", "privateViewKey": "{self.secret_view_key}", "restoreHeight": {self.height}}}'

    def get_qr_type(self):
        return QrType.WALLET_VIEW_ONLY_JSON


class MoneroKeyImageQrEncoder(UrQrEncoder):

    def __init__(self, key_images_blob: bytes, qr_density: QrDensity):
        super().__init__(
            XMR_KEY_IMAGE.type,
            XmrKeyImage(key_images_blob).to_cbor(),
            qr_density
        )

    def get_qr_type(self):
        return QrType.XMR_KEYIMAGE_UR


class MoneroSignedTxQrEncoder(UrQrEncoder):

    def __init__(self, signed_tx: bytes, qr_density: QrDensity):
        super().__init__(
            XMR_TX_SIGNED.type,
            XmrTxSigned(signed_tx).to_cbor(),
            qr_density
        )

    def get_qr_type(self):
        return QrType.XMR_TX_SIGNED_UR
