from ots.seed import (
    MoneroSeed,
    Polyseed
)
from ots.seed_language import SeedLanguage
from ots.enums import SeedType
from os import urandom
from xmrsigner.helpers.qr import QR
from xmrsigner.helpers.ur2.bytewords import decode
from xmrsigner.models.decode_qr import (
    DecodeQR,
    DecodeQRStatus
)
from xmrsigner.models.encode_qr import EncodeQR
from xmrsigner.models.qr_type import QrType


def run_encode_decode_test(entropy: bytes, mnemonic_length, qr_type):
    """ Helper method to re-run multiple variations of the same encode/decode test """
    print(entropy)
    seed_phrase = MoneroSeed.create(entropy).phrase(SeedLanguage.fromCode('en')).insecure().split()
    print(seed_phrase)
    assert len(seed_phrase) == mnemonic_length
    e = EncodeQR(seed_phrase=seed_phrase, qr_type=qr_type)
    data = e.next_part()
    print(data)
    qr = QR()
    image = qr.qrimage(
        data=data,
        width=240,
        height=240,
        border=3
    )
    decoder = DecodeQR()
    status = decoder.add_image(image)
    assert status == DecodeQRStatus.COMPLETE
    decoded_seed_phrase = decoder.get_seed_phrase()
    print(decoded_seed_phrase)
    assert seed_phrase == decoded_seed_phrase


def test_standard_seedqr_encode_decode_():
    """ Should encode 24- and 12- word mnemonics to Standard SeedQR format and decode
        them back again to their original mnemonic seed phrase.
    """
    # 24-word seed
    run_encode_decode_test(urandom(32), mnemonic_length=24, qr_type=QrType.SEED_SEEDQR)
    # 12-word seed
    run_encode_decode_test(urandom(16), mnemonic_length=12, qr_type=QrType.SEED_SEEDQR)



def test_compact_seedqr_encode_decode():
    """ Should encode 24- and 12- word mnemonics to CompactSeedQR format and decode
        them back again to their original mnemonic seed phrase.
    """
    # 24-word seed
    run_encode_decode_test(urandom(32), mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed
    run_encode_decode_test(urandom(16), mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)



def test_compact_seedqr_handles_null_bytes():
    """ Should properly encode a CompactSeedQR with null bytes (b'\x00') in the input
        entropy and decode it back to the original mnemonic seed.
    """
    # 24-word seed, null bytes at the front
    entropy = b'\x00' + urandom(31)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 24-word seed, null bytes in the middle
    entropy = urandom(10) + b'\x00' + urandom(21)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 24-word seed, null bytes at the end
    entropy = urandom(31) + b'\x00'
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 24-word seed, multiple null bytes
    entropy = urandom(5) + b'\x00' + urandom(5) + b'\x00' + urandom(20)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 24-word seed, multiple null bytes in a row
    entropy = urandom(10) + b'\x00\x00' + urandom(20)
    run_encode_decode_test(entropy, mnemonic_length=24, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed, null bytes at the beginning
    entropy = b'\x00' + urandom(15)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed, null bytes in the middle
    entropy = urandom(5) + b'\x00' + urandom(10)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed, null bytes at the end
    entropy = urandom(15) + b'\x00'
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed, multiple null bytes
    entropy = urandom(5) + b'\x00' + urandom(5) + b'\x00' + urandom(4)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)

    # 12-word seed, multiple null bytes in a row
    entropy = urandom(10) + b'\x00\x00' + urandom(4)
    run_encode_decode_test(entropy, mnemonic_length=12, qr_type=QrType.SEED_COMPACTSEEDQR)
