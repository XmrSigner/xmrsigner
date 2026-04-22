import pytest
from mock import MagicMock
from xmrsigner.models import DecodeQR, QrType


def test_short_4_letter_mnemonic_qr():
    short_nm = "heig demi usel trap grow lion foun off key clow tran enro"
    d = DecodeQR()
    d.add_data(short_nm)
    assert d.is_complete
    assert d.get_seed_phrase() == ["height", "demise", "useless", "trap", "grow", "lion", "found", "off", "key", "clown", "transfer", "enroll"]


def test_seed_qr():
    seed = "121802020768124106400009195602431595117715840445"
    d = DecodeQR()
    d.add_data(seed)
    assert d.qr_type == QrType.SEED__SEEDQR
    assert d.get_seed_phrase() == "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split()
