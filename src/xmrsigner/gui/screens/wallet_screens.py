from dataclasses import dataclass

from xmrsigner.gui.screens.screen import ButtonListScreen
from xmrsigner.gui.components import (
    IconConstants,
    GUIConstants
)

@dataclass
class WalletOptionsScreen(ButtonListScreen):

    # Customize defaults
    is_bottom_list: bool = True
    fingerprint: str = None
    polyseed: bool = False
    my_monero: bool = False

    def __post_init__(self):
        self.top_nav_icon_name = IconConstants.FINGERPRINT
        self.top_nav_icon_color = GUIConstants.FINGERPRINT_POLYSEED_COLOR if self.polyseed else GUIConstants.FINGERPRINT_MONERO_SEED_COLOR if not self.my_monero else GUIConstants.FINGERPRINT_MY_MONERO_SEED_COLOR
        self.title = f'Wallet: {self.fingerprint}'
        self.is_button_text_centered = False
        self.is_bottom_list = True
        super().__post_init__()
