from ots.ots import Ots
from ots.seed import (
    Seed,
    Polyseed,
    MoneroSeed,
    LegacySeed,
    Network,
    SeedLanguage,
    SeedType
)
from ots.address import Address
from ots.seed_jar import SeedJar

from dataclasses import dataclass
from time import time, sleep

from PIL import Image
from PIL.ImageOps import autocontrast

from xmrsigner.controller import Flow
from xmrsigner.gui.button_data import ButtonData
from xmrsigner.gui.components import FontAwesome, Theme, IconConstants
from xmrsigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    seed_screens
)
from xmrsigner.gui.screens.monero_screens import DateOrBlockHeightScreen
from xmrsigner.gui.screens.tools_screens import (
    ToolsCalcFinalWordFinalizePromptScreen,
    ToolsCalcFinalWordScreen,
    ToolsCoinFlipEntryScreen,
    ToolsDiceEntropyEntryScreen,
    ToolsImageEntropyFinalImageScreen,
    ToolsImageEntropyLivePreviewScreen,
    ToolsCalcFinalWordDoneScreen,
)
from xmrsigner.helpers.entropy import (
    CameraEntropy,
    DiceEntropy
)
from xmrsigner.models.pending_seed import (
    PendingSeed,
    PendingSeedPhrase,
    PendingSeedIndices,
    PendingSeedEntropy
)
from xmrsigner.models.wordlists import words
from xmrsigner.models.settings_definition import (
    Setting,
    Option
)
from xmrsigner.models.monero_encoder import MoneroAddressEncoder
from xmrsigner.views.seed_views import (
    SeedDiscardView,
    SeedFinalizeView,
    SeedMnemonicEntryView,
    SeedWordsWarningView,
    SeedOptionsView
)
from xmrsigner.views.view import (
    View,
    Destination,
    BackStackView,
    DireWarningScreen
)


class ToolsMenuView(View):

    def run(self):
        CREATE = ButtonData('Create Seed').with_icon(FontAwesome.PLUS)
        EXPLORER = ButtonData('Address Explorer').with_icon(FontAwesome.LIST)
        ADDRESS = ButtonData('Verify address').with_icon(IconConstants.SCAN)
        button_data: list[ButtonData] = [CREATE, EXPLORER, ADDRESS]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Tools",
            is_button_text_centered=False,
            button_data=button_data
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == CREATE:
            return Destination(ToolsCreateSeedTypeView, clear_history=True)
        if button_data[selected_menu_num] == EXPLORER:
            return Destination(ToolsAddressExplorerSelectSourceView)
        if button_data[selected_menu_num] == ADDRESS:
            from xmrsigner.views.scan_views import ScanAddressView
            return Destination(ScanAddressView)


class ToolsCreateSeedTypeView(View):

    def run(self):
        MONERO = ButtonData('Monero')
        POLYSEED = ButtonData('Polyseed')
        button_data = [MONERO, POLYSEED]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Entropy source",
            is_button_text_centered=False,
            button_data=button_data
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if self.controller.pending_seed is None:
            self.controller.pending_seed = PendingSeedEntropy()
        if button_data[selected_menu_num] == MONERO:
            self.controller.pending_seed.type = SeedType.MONERO
        if button_data[selected_menu_num] == POLYSEED:
            self.controller.pending_seed.type = SeedType.POLYSEED
        return Destination(ToolsNetworkView)


"""****************************************************************************
    Image entropy Views
****************************************************************************"""
class ToolsImageEntropyLivePreviewView(View):

    def run(self):
        self.controller.image_entropy_preview_frames = None
        ret = ToolsImageEntropyLivePreviewScreen().display()
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        self.controller.image_entropy_preview_frames = ret
        return Destination(ToolsImageEntropyFinalImageView)


class ToolsImageEntropyFinalImageView(View):

    def run(self):
        if not self.controller.image_entropy_final_image:
            from xmrsigner.hardware.camera import Camera
            # Take the final full-res image
            camera = Camera.get_instance()
            camera.start_single_frame_mode(resolution=(720, 480))
            sleep(0.25)
            self.controller.image_entropy_final_image = camera.capture_frame()
            camera.stop_single_frame_mode()
        # Prep a copy of the image for display. The actual image data is 720x480
        # Present just a center crop and resize it to fit the screen and to keep some of
        #   the data hidden.
        display_version = autocontrast(
            self.controller.image_entropy_final_image,
            cutoff=2
        ).crop(
            (120, 0, 600, 480)
        ).resize(
            (self.canvas_width, self.canvas_height), Image.BICUBIC
        )
        ret = ToolsImageEntropyFinalImageScreen(
            final_image=display_version
        ).display()
        if ret == RET_CODE__BACK_BUTTON:
            # Go back to live preview and reshoot
            self.controller.image_entropy_final_image = None
            return Destination(BackStackView)
        return Destination(ToolsImageEntropySeedView)


class ToolsNetworkView(View):

    def run(self):
        networks: list[NetworkChoice] = self.settings.get_value(Setting.NETWORKS)
        network: Network|None = None
        if len(networks) == 1:
            network = networks[0].value
        else:
            if len(networks) == 0:
                networks = NetworkChoice.all()
            button_data: list[ButtonData] = [
                ButtonData(e.display)
                for e in networks
            ]
            selected_menu_num = self.run_screen(
                ButtonListScreen,
                title='Choose Network',
                is_button_text_centered=False,
                button_data=button_data
            )
            if selected_menu_num == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            network = networks[selected_menu_num].value
        print(f'NETWORK: {network}')
        self.controller.pending_seed.network = network
        return Destination(ToolsDateView)


class ToolsDateView(View):

    def run(self):
        ret = self.run_screen(
            DateOrBlockHeightScreen,
            network = self.controller.pending_seed.network,
            is_block_height = False,
            current_date = self.controller.date if self.controller.timestamp_set else None
        )
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        self.controller.pending_seed.height = int(ret)
        self.controller.timestamp = Ots.timestampFromHeight(
            self.controller.pending_seed.height,
            self.controller.pending_seed.network
        )
        return Destination(ToolsPasswordView)


class ToolsPasswordView(View):

    def run(self):
        if self.controller.pending_seed.type != SeedType.POLYSEED:
            return Destination(ToolsPassphraseView)
        ret = self.run_screen(
            ButtonListScreen,
            title='Add password?',
            is_button_text_centered=False,
            button_data=[ButtonData('Yes'), ButtonData('No')]
        )
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if ret == 0:  # Yes
            ret = self.run_screen(
                seed_screens.SeedAddPassphraseScreen,
                passphrase=self.controller.pending_seed.password,
                title='Enter password'
            )
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            # The new passphrase will be the return value; it might be empty.
            self.controller.pending_seed.password = ret
        return Destination(ToolsPassphraseView)


class ToolsPassphraseView(View):

    def run(self):
        add_passphrase: Option = self.settings.get_value(Setting.MONERO_SEED_PASSPHRASE if self.controller.pending_seed.type == SeedType.MONERO else Setting.POLYSEED_PASSPHRASE)
        if add_passphrase == Option.ENABLED:
            ret = self.run_screen(
                ButtonListScreen,
                title='Add passphrase?',
                is_button_text_centered=False,
                button_data=[ButtonData('Yes'), ButtonData('No')]
            )
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            if ret == 0:  # Yes
                add_passphrase = Option.REQUIRED
        if add_passphrase == Option.REQUIRED:
            ret = self.run_screen(
                seed_screens.SeedAddPassphraseScreen,
                passphrase=self.controller.pending_seed.passphrase,
                title='Enter passphrase'
            )
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            # The new passphrase will be the return value; it might be empty.
            self.controller.pending_seed.password = ret
        return Destination(ToolsCreateSeedMethodView)


class ToolsCreateSeedMethodView(View):

    def __init__(
        self,
        secure_only: bool = False
    ):
        super().__init__()
        self.secure_only: bool = secure_only

    def run(self):
        IMAGE = ButtonData('Camera').with_icon(FontAwesome.CAMERA)
        DICE = ButtonData('Dice').with_icon(FontAwesome.DICE)
        KEYBOARD = ButtonData('Pick own words').with_icon(FontAwesome.KEYBOARD)
        button_data = [IMAGE, DICE]
        if (
            not self.secure_only
            and self.settings.get_value(Setting.LOW_SECURITY) == Option.ENABLED
        ):
            button_data.append(KEYBOARD)
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Entropy source",
            is_button_text_centered=False,
            button_data=button_data
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == IMAGE:
            return Destination(ToolsImageEntropyLivePreviewView)
        if button_data[selected_menu_num] == DICE:
            return Destination(ToolsDiceEntropyEntryView)
        if button_data[selected_menu_num] == KEYBOARD:
            return Destination(ToolsCalcFinalWordWarningView)


class ToolsImageEntropySeedView(View):

    def run(self):
        entropy: CameraEntropy = CameraEntropy(
            self.controller.image_entropy_preview_frames,
            self.controller.image_entropy_final_image
        )
        self.controller.pending_seed.entropy = bytes(entropy)
        self.controller.image_entropy_preview_frames = None
        self.controller.image_entropy_final_image = None
        # Cannot return BACK to this View
        return Destination(SeedWordsWarningView, clear_history=True)


"""****************************************************************************
    Dice rolls Views
****************************************************************************"""
class ToolsDiceEntropyEntryView(View):

    def __init__(self):
        super().__init__()

    def run(self):
        required_chars: int = 100 if self.controller.pending_seed.type == SeedType.MONERO else 59  # 256bit / 152bit
        required_entropy: int = 256 if self.controller.pending_seed.type == SeedType.MONERO else 152
        ret = ToolsDiceEntropyEntryScreen(
            return_after_n_chars=required_chars,
        ).display()
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        self.controller.pending_seed.entropy = bytes(DiceEntropy(ret, required_entropy))
        # Cannot return BACK to this View
        return Destination(SeedWordsWarningView, clear_history=True)



"""****************************************************************************
    Calc final word Views
****************************************************************************"""
class ToolsCalcFinalWordWarningView(View):
    def __init__(self):
        super().__init__()

    def run(self):
        destination = Destination(
            ToolsCalcFinalWordNumWordsView,
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(Setting.DIRE_WARNINGS) == Option.DISABLED:
            return destination

        MORE_SECURE = ButtonData('Choose secure way')
        AWARE = ButtonData("I know what I'm doing")
        button_data = [MORE_SECURE, AWARE]

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title='Low Entropy Warning',
            show_back_button=False,
            status_headline='Are you sure?',
            text='The most insecure way, if not random.',
            button_data=button_data,
            allow_text_overflow=True
        )

        if button_data[selected_menu_num] == AWARE:
            # User clicked "I Understand"
            return destination

        elif button_data[selected_menu_num] == MORE_SECURE:
            # return Destination(BackStackView)
            return Destination(ToolsCreateSeedMethodView, view_args={'secure_only': True}, clear_history=True)


class ToolsCalcFinalWordNumWordsView(View):

    def run(self):
        if self.settings.get_value(Setting.LOW_SECURITY) == Option.ENABLED:
            THIRTEEN = ButtonData('13 words')
            TWENTY_FIVE = ButtonData('25 words')

            button_data = [THIRTEEN, TWENTY_FIVE]
            selected_menu_num = ButtonListScreen(
                title='Mnemonic Length',
                is_bottom_list=True,
                is_button_text_centered=True,
                button_data=button_data,
            ).display()
            if selected_menu_num == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            if button_data[selected_menu_num] == THIRTEEN:
                self.controller.pending_seed = PendingSeedPhrase(isLegacy=True)
                return Destination(SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True))
            if button_data[selected_menu_num] == TWENTY_FIVE:
                self.controller.pending_seed = PendingSeedPhrase()
                return Destination(
                    SeedMnemonicEntryView, view_args={
                            'is_calc_final_word': True
                    }
                )
        return Destination(
            SeedMnemonicEntryView,
            view_args={
                'is_calc_final_word': True
            }
        )


class ToolsCalcFinalWordShowFinalWordView(View):  # TODO: 2024-06-04, rename, because it is missleading, the only thing what will be calculated is the checksum word

    def __init__(self, coin_flips: str|None = None):
        super().__init__()
        self.coin_flips: str|None = coin_flips

    def run(self):
        pending_seed: PendingSeed = self.controller.pending_seed
        pending_seed.mnemonic = pending_seed.seed(
                without_checksum=True
            ).phrase(
                SeedLanguage.fromCode(
                    self.settings.get_value(
                        Setting.MONERO_WORDLIST_LANGUAGE
                    ).value
                )
            ).insecure()
        return Destination(ToolsCalcFinalWordDoneView)


class ToolsCalcFinalWordDoneView(View):

    def run(self):
        pending_seed = self.controller.pending_seed
        seed: Seed = pending_seed.seed()
        NEXT = ButtonData('Next')
        DISCARD = ButtonData.DISCARD()
        button_data = [NEXT, DISCARD]
        selected_menu_num = ToolsCalcFinalWordDoneScreen(
            final_word=pending_seed.get(-1),
            mnemonic_word_length=pending_seed.length,
            fingerprint=seed.fingerprint,
            button_data=button_data,
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == NEXT:
            from xmrsigner.views.seed_views import SeedNetworkView
            pending_seed.pre_filled = True
            return Destination(SeedNetworkView)
        if button_data[selected_menu_num] == DISCARD:
            from xmrsigner.views.view import MainMenuView
            self.controller.pending_seed = None
            return Destination(MainMenuView, clear_history=True)


"""****************************************************************************
    Address Explorer Views
****************************************************************************"""
class ToolsAddressExplorerSelectSourceView(View):

    SCAN_SEED = ("Scan a seed", IconConstants.QRCODE)
    SCAN_WALLET = ("Scan wallet", IconConstants.QRCODE)
    TYPE_13WORD = ("Enter 13-word seed", FontAwesome.KEYBOARD)
    TYPE_25WORD = ("Enter 25-word seed", FontAwesome.KEYBOARD)
    TYPE_POLYSEED = ("Enter Polyseed", FontAwesome.KEYBOARD)

    def run(self):
        button_data = [
            ButtonData(seed.fingerprint).with_icon(IconConstants.FINGERPRINT)
            for seed in SeedJar.items()
        ]
        button_data = button_data + [
            self.SCAN_SEED,
            self.SCAN_WALLET,
            self.TYPE_13WORD,
            self.TYPE_25WORD,
            self.TYPE_POLYSEED
        ]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Address Explorer",
            button_data=button_data,
            is_button_text_centered=False,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Most of the options require us to go through a side flow(s) before we can
        # continue to the address explorer. Set the Controller-level flow so that it
        # knows to re-route us once the side flow is complete.
        self.controller.resume_main_flow = Flow.ADDRESS_EXPLORER

        if SeedJar.count() > 0 and selected_menu_num < SeedJar.count():
            # User selected one of the n seeds
            return Destination(
                ToolsAddressExplorerSeedAccountsView,
                view_args={
                    'seed': SeedJar.forFingerprint(button_data[selected_menu_num].label)
                }
            )
        if button_data[selected_menu_num] == self.SCAN_SEED:
            from xmrsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)
        if button_data[selected_menu_num] == self.SCAN_WALLET:
            from xmrsigner.views.scan_views import ScanWalletDescriptorView
            return Destination(ScanWalletDescriptorView)
        if button_data[selected_menu_num] in [self.TYPE_13WORD, self.TYPE_25WORD]:
            self.controller.pending_seed = PendingSeedPhrase(
                isLegacy=button_data[selected_menu_num] == self.TYPE_13WORD
            )
        if button_data[selected_menu_num] == self.TYPE_POLYSEED:
            self.controller.pending_seed = PendingSeedPhrase(seed_type=SeedType.POLYSEED)
        if self.controller.pending_seed is not None:
            from xmrsigner.views.seed_views import SeedNetworkView
            return Destination(SeedNetworkView)


class ToolsAddressExplorerSeedAccountsView(View):

    def __init__(
        self,
        seed: Seed
    ):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        data: list[ButtonData] = []
        try:
            from xmrsigner.gui.screens.screen import LoadingScreenThread
            self.loading_screen = LoadingScreenThread(text="Calculating addrs...")
            self.loading_screen.start()
            data = [
                ButtonData(f'{i:02d}  {a.base58[:7]}...{a.base58[-7:]}', right_icon_name=IconConstants.CHEVRON_RIGHT)
                for i, a in enumerate(self.seed.wallet.address(j) for j in range(Ots.maxAccountDepth()))
            ]
        finally:
            # Everything is set. Stop the loading screen
            self.loading_screen.stop()
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=self.seed.address.fingerprint,
            button_data=data,
            button_font_name=Theme.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            button_font_size=Theme.BUTTON_FONT_SIZE + 4,
            is_button_text_centered=False,
            is_bottom_list=True
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # If we entered this flow via an already-loaded seed's SeedOptionsView, we
            # need to clear the `resume_main_flow` so that we don't get stuck in a
            # SeedOptionsView redirect loop.
            # TODO: Refactor to a cleaner `BackStack.get_previous_View_cls()`
            if len(self.controller.back_stack) > 1 and self.controller.back_stack[-2].View_cls == SeedOptionsView:
                # The BackStack has the current View on the top with the real "back" in second position.
                self.controller.resume_main_flow = None
                self.controller.address_explorer_data = None
            return Destination(BackStackView)

        if selected_menu_num < Ots.maxAccountDepth():
            return Destination(
                ToolsAddressExplorerAddressListView,
                view_args={
                    'seed': self.seed,
                    'account': selected_menu_num
                }
            )


class ToolsAddressExplorerAddressListView(View):

    def __init__(
        self,
        seed: Seed|None = None,
        account: int = 0,
        start_index: int = 0,
        selected_button_index: int = 0,
        initial_scroll: int = 0
    ):
        super().__init__()
        if seed is None:
            raise Exception('seed can not be none')
        self.seed: Seed = seed
        self.account: int = account
        self.start_index: int = start_index
        self.selected_button_index: int = selected_button_index
        self.initial_scroll: int = initial_scroll

    def run(self):
        self.loading_screen = None

        button_data: list[ButtonData] = []
        try:
            from xmrsigner.gui.screens.screen import LoadingScreenThread
            self.loading_screen = LoadingScreenThread(text="Calculating addrs...")
            self.loading_screen.start()
            button_data = [
                ButtonData(f'{i:03d} {a.base58[:5]}...{a.base58[-5:]}', right_icon_name=IconConstants.CHEVRON_RIGHT)
                for i, a in enumerate(self.seed.wallet.address(self.account, j) for j in range(Ots.maxIndexDepth()))
            ]
        finally:
            # Everything is set. Stop the loading screen
            self.loading_screen.stop()

#        button_data.append(
#            ButtonData(
#                'Next {}'.format(addrs_per_screen),
#                right_icon_name=IconConstants.CHEVRON_RIGHT
#            )
#        )
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=f'{self.seed.fingerprint} Account {self.account:02d}',
            button_data=button_data,
            button_font_name=Theme.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            button_font_size=Theme.BUTTON_FONT_SIZE + 4,
            is_button_text_centered=False,
            is_bottom_list=True,
            selected_button=self.selected_button_index,
            scroll_y_initial_offset=self.initial_scroll,
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if selected_menu_num == Ots.maxIndexDepth():
            # User clicked NEXT
            return Destination(
                ToolsAddressExplorerAddressListView,
                view_args={
                    'seed': self.seed
                }
            )
        # Preserve the list's current scroll so we can return to the same spot
        initial_scroll = self.screen.buttons[0].scroll_y
        # index = selected_menu_num + self.start_index
        return Destination(
            ToolsAddressExplorerAddressView,
            view_args={
                'seed': self.seed,
                'account': self.account,
                'index': selected_menu_num,
                'address': self.seed.wallet.address(self.account, selected_menu_num),
                'start_index': self.start_index,
                'parent_initial_scroll': initial_scroll
            },
            skip_current_view=True
        )


class ToolsAddressExplorerAddressView(View):

    def __init__(
        self,
        seed: Seed,
        account: int,
        index: int,
        address: Address,
        start_index: int,
        parent_initial_scroll: int = 0
    ):
        super().__init__()
        self.seed: Seed = seed
        self.account: int = account
        self.index: int = index
        self.address: Address = address
        self.start_index: int = start_index
        self.parent_initial_scroll: int = parent_initial_scroll

    def run(self):
        from xmrsigner.gui.screens.screen import QRDisplayScreen
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=MoneroAddressEncoder(self.address.base58),
        )
        # Exiting/Cancelling the QR display screen always returns to the list
        return Destination(
            ToolsAddressExplorerAddressListView,
            view_args={
                'seed': self.seed,
                'account': self.account,
                'start_index': self.start_index,
                'selected_button_index': self.index - self.start_index,
                'initial_scroll': self.parent_initial_scroll
            },
            skip_current_view=True
        )
