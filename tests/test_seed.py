import pytest
from mock import MagicMock

from ots.seed_language import SeedLanguage
from ots.enums import SeedType, Network
from ots.seed import (
    Seed,
    MoneroSeed,
    Polyseed,
    LegacySeed
)


def test_seed():  # TODO: adapt to XMR
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	assert seed.seed_bytes == b'q\xb3\xd1i\x0c\x9b\x9b\xdf\xa7\xd9\xd97H\xa8,\xa7\xd9>\xeck\xc2\xf5ND?, \x88-\x07\x9aa\xc5\xee\xb7\xbf\xc4x\xd6\x07 X\xb6}?M\xaa\x05\xa6\xa7(>\xbf\x03\xb0\x9d\xef\xed":\xdf\x88w7'
	assert seed.mnemonic_str == "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"
	assert seed.passphrase == ""
