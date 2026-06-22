from enum import Enum


class QrType(Enum):
    '''
    Used with DecodeQR to communicate qr encoding type
    '''
    UR2 = 'ur2'

    SEED_QR = 'seed_seedqr'
    COMPACT_SEED_QR = 'seed_compactseedqr'
    SEED_UR2 = 'seed_ur2'
    MNEMONIC = 'seed_mnemonic'

    SETTINGS = 'settings'

    MONERO_ADDRESS = 'monero_address'
    MONERO_WALLET = 'monero_wallet'
    XMR_OUTPUT_UR = 'xmr_output_ur'
    XMR_KEYIMAGE_UR = 'xmr_keyimage_ur'
    XMR_TX_UNSIGNED_UR = 'xmr_unsigned_tx_ur'
    XMR_TX_SIGNED_UR = 'xmr_signed_tx_ur'

    SIGN_MESSAGE = "sign_message"

    WALLET_VIEW_ONLY = 'wallet_view_only'
    WALLET_VIEW_ONLY_JSON = 'wallet_view_only_json'
    BYTES_UR = 'bytes_ur'

    INVALID = 'invalid'
    DATE = 'date'
    TIMESTAMP = 'timestamp'
