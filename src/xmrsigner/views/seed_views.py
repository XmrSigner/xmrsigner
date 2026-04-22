from ots.seed import Seed
from ots.seed_language import SeedLanguage
from ots.seed_jar import SeedJar
from ots.enums import Network, SeedType

from random import random, shuffle, choice
from math import ceil

from xmrsigner.controller import Controller, Flow
from xmrsigner.gui.components import (
    GUIConstants,
    FontAwesomeIconConstants,
    IconConstants
)
from xmrsigner.gui.button_data import ButtonData, FingerprintButtonData
from xmrsigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    WarningScreen,
    DireWarningScreen,
    seed_screens
)
from xmrsigner.gui.screens.screen import (
    LargeIconStatusScreen,
    QRDisplayScreen
)
from xmrsigner.gui.screens.monero_screens import DateOrBlockHeightScreen
from xmrsigner.models.decode_qr import DecodeQR
from xmrsigner.models.seed_encoder import SeedQrEncoder, CompactSeedQrEncoder
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.pending_seed import PendingSeed
from xmrsigner.models.settings import Settings, Setting
from xmrsigner.models.settings_definition import Network as NetworkChoice
from xmrsigner.models.threads import BaseThread, ThreadsafeCounter
from xmrsigner.models.wordlists import words
from xmrsigner.views.wallet_views import (
    WalletViewKeyQRView,
    WalletViewKeyJsonQRView,
    LoadWalletView,
    ImportOutputsView,
    ExportKeyImagesView
)
from xmrsigner.views.view import (
    NotYetImplementedView,
    OptionDisabledView,
    View,
    Destination,
    BackStackView,
    MainMenuView
)


class SeedsMenuView(View):

    LOAD = 'Load a seed'

    def __init__(self):
        super().__init__()

    def run(self):
        if SeedJar.count() < 1:
            # Nothing to do here unless we have a seed loaded
            return Destination(LoadSeedView, clear_history=True)
        button_data = [
            button_data.append(
                    FingerprintButtonData(
                    seed.fingerprint,
                    seed.type == SeedType.POLYSEED,
                    seed.isLegacy
                )
            )
            for seed in SeedJar.seeds()
        ]
        button_data.append('Load a seed')
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title='In-Memory Seeds',
            is_button_text_centered=False,
            button_data=button_data
        )
        if SeedJar.count() > 0 and selected_menu_num < SeedJar.count():
            return Destination(SeedOptionsView, view_args={'seed': SeedJar.forIndex(selected_menu_num)})
        if selected_menu_num == SeedJar.count():
            return Destination(LoadSeedView)
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


"""
****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************
"""
class LoadSeedView(View):

    SEED_QR = ButtonData('Scan a SeedQR').with_icon(IconConstants.QRCODE)
    TYPE_13WORD = ButtonData('Enter 13-word seed').with_icon(FontAwesomeIconConstants.KEYBOARD)
    TYPE_25WORD = ButtonData('Enter 25-word seed').with_icon(FontAwesomeIconConstants.KEYBOARD)
    TYPE_POLYSEED = ButtonData('Enter Polyseed').with_icon(FontAwesomeIconConstants.KEYBOARD)
    CREATE = ButtonData('Create a seed').with_icon(IconConstants.PLUS)

    def run(self):
        button_data=[
            self.SEED_QR,
            self.TYPE_13WORD,
            self.TYPE_25WORD,
            self.TYPE_POLYSEED,
            self.CREATE,
        ]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title='Load A Seed',
            is_button_text_centered=False,
            button_data=button_data
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == self.SEED_QR:
            from xmrsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)
        if button_data[selected_menu_num] == self.TYPE_13WORD:
            self.controller.pending_seed = PendingSeed(isLegacy=True)
            return Destination(SeedMnemonicEntryView)
        if button_data[selected_menu_num] == self.TYPE_25WORD:
            self.controller.jar.pending_seed = PendingSeed()
            return Destination(SeedMnemonicEntryView)
        if button_data[selected_menu_num] == self.TYPE_POLYSEED:
            self.controller.pending_seed = PendingSeed(type=SeedType.POLYSEED)
            return Destination(PolyseedMnemonicEntryView)
        if button_data[selected_menu_num] == self.CREATE:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)


class SeedMnemonicEntryView(View):

    def __init__(self, cur_word_index: int = 0, is_calc_final_word: bool=False):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.pending_seed.get(cur_word_index)
        self.is_calc_final_word = is_calc_final_word

    def run(self):
        ret = self.run_screen(
            seed_screens.SeedMnemonicEntryScreen,
            title=f'Seed Word #{self.cur_word_index + 1}',  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ['a'],
            wordlist=words(SeedType.MONERO, self.settings.get_value(Setting.MONERO_WORDLIST_LANGUAGE)),
        )
        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(BackStackView)
            self.controller.pending_seed = None
            return Destination(MainMenuView)
        # ret will be our new mnemonic word
        self.controller.pending_seed.set(ret, self.cur_word_index)
        if self.is_calc_final_word and self.cur_word_index == self.controller.pending_seed.length - 2:
            # Time to calculate the last word. User must decide how they want to specify
            # the last bits of entropy for the final word.
            from xmrsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView
            return Destination(ToolsCalcFinalWordShowFinalWordView, view_args=dict(coin_flips="0" * 7))
        if self.is_calc_final_word and self.cur_word_index == self.controller.pending_seed.length - 1:
            # Time to calculate the last word. User must either select a final word to
            # contribute entropy to the checksum word OR we assume 0 ("abandon").
            from xmrsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView
            return Destination(ToolsCalcFinalWordShowFinalWordView)
        if self.cur_word_index < self.controller.pending_seed.length - 1:
            return Destination(
                SeedMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1,
                    "is_calc_final_word": self.is_calc_final_word
                }
            )
        # Attempt to finalize the mnemonic
        try:
            self.controller.pending_seed.seed()
        except:
            return Destination(SeedMnemonicInvalidView)
        return Destination(SeedFinalizeView)


class PolyseedMnemonicEntryView(SeedMnemonicEntryView):

    def __init__(self, cur_word_index: int = 0):
        super().__init__(cur_word_index, False)

    def run(self):
        ret = self.run_screen(
            seed_screens.SeedMnemonicEntryScreen,
            title=f"Polyseed Word #{self.cur_word_index + 1}",  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ['a'],
            wordlist=words(SeedType.POLYSEED, self.settings.get_value(Setting.POLYSEED_WORDLIST_LANGUAGE)),
        )
        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(BackStackView)
            self.controller.pending_seed = None
            return Destination(MainMenuView)
        # ret will be our new mnemonic word
        self.controller.pending_seed.set(ret, self.cur_word_index)
        if self.cur_word_index < self.controller.pending_seed.length - 1:
            return Destination(
                PolyseedMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1
                }
            )
        # Attempt to finalize the mnemonic
        try:
            self.controller.pending_seed.seed()
        except:
            return Destination(SeedMnemonicInvalidView, view_args={'polyseed': True})
        return Destination(SeedFinalizeView)


class SeedMnemonicInvalidView(View):

    EDIT = ButtonData('Review & Edit')
    DISCARD = ButtonData.DISCARD

    def __init__(self):
        super().__init__()
        self.polyseed = self.controller.pending_seed.type == SeedType.POLYSEED

    def run(self):
        button_data = [self.EDIT, self.DISCARD]
        selected_menu_num = self.run_screen(
            WarningScreen,
            title="Invalid Mnemonic!",
            status_headline=None,
            text=f"Checksum failure; not a valid seed phrase.",
            show_back_button=False,
            button_data=button_data,
        )
        if button_data[selected_menu_num] == self.EDIT:
            return Destination(
                PolyseedMnemonicEntryView if self.polyseed else SeedMnemonicEntryView,
                view_args={"cur_word_index": 0}
            )
        if button_data[selected_menu_num] == self.DISCARD:
            self.controller.pending_seed = None
            return Destination(MainMenuView)


class SeedFinalizeView(View):

    FINALIZE = ButtonData('Done')
    PASSPHRASE = ButtonData('Add Passphrase').with_icon(FontAwesomeIconConstants.LOCK)

    def __init__(self):
        super().__init__()
        self.pending_seed: PendingSeed = self.controller.pending_seed

    def run(self):
        networks: list[NetworkChoice] = self.settings.get_value(Setting.NETWORKS)
        if len(networks) == 1:
            self.pending_seed.network = networks[0].value
        if len(networks) > 1:
            ret = self.run_screen(
                ButtonListScreen,
                title='Choose Network',
                button_data=[ButtonData(n.display) for n in networks]
            )
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            self.pending_seed.network = networks[ret].value
        if self.pending_seed.type != SeedType.POLYSEED:
            ret = self.run_screen(DateOrBlockHeightScreen)
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            if type(ret) == str:
                self.pending_seed.height = int(ret)
        button_data = []
        button_data.append(self.FINALIZE)
        if (
                self.pending_seed.type != SeedType.POLYSEED
                and self.settings.get_value(Setting.MONERO_SEED_PASSPHRASE) == Option.ENABLED
            ) or (
                self.pending_seed.type == SeedType.POLYSEED
                and self.settings.get_value(Settings.POLYSEED_PASSPHRASE) == OPTION.ENABLED
            ):
            button_data.append(self.PASSPHRASE)
        selected_menu_num = self.run_screen(
            seed_screens.SeedFinalizeScreen,
            fingerprint=self.seed.fingerprint,
            polyseed=self.pending_seed.type == SeedType.POLYSEED,
            button_data=button_data,
        )
        if button_data[selected_menu_num] == self.FINALIZE:
            seed = SeedJar.transferIn(self.controller.pending_seed.seed())
            return Destination(SeedOptionsView, view_args={'seed': seed}, clear_history=True)
        if button_data[selected_menu_num] == self.PASSPHRASE:
            return Destination(SeedAddPassphraseView)


class SeedAddPassphraseView(View):

    def __init__(self):
        super().__init__()
        self.pending_seed = self.controller.pending_seed

    def run(self):
        ret = self.run_screen(seed_screens.SeedAddPassphraseScreen, passphrase=self.pending_seed.passphrase)
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        # The new passphrase will be the return value; it might be empty.
        self.pending_seed.passphrase = ret
        if len(self.pending_seed.passphrase) > 0:
            return Destination(SeedReviewPassphraseView)
        return Destination(SeedFinalizeView)


class SeedReviewPassphraseView(View):
    '''
    Display the completed passphrase back to the user.
    '''

    EDIT = ButtonData('Edit passphrase')
    DONE = ButtonData('Done')

    def __init__(self):
        super().__init__()
        self.pending_seed = self.controller.pending_seed

    def run(self):
        # Get the before/after fingerprints
        passphrase = self.pending_seed.passphrase
        fingerprint_with = self.pending_seed.seed().fingerprint
        self.pending_seed.passphrase = None
        fingerprint_without = self.pending_seed.seed().fingerprint
        self.pending_seed.passphrase = passphrase
        button_data = [self.EDIT, self.DONE]
        # Because we have an explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = self.run_screen(
            seed_screens.SeedReviewPassphraseScreen,
            fingerprint_without=fingerprint_without,
            fingerprint_with=fingerprint_with,
            passphrase=self.seed.passphrase,
            polyseed=self.seed.type == SeedType.POLYSEED,
            my_monero=self.seed.isLegacy,
            button_data=button_data,
            show_back_button=False,
        )
        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)
        if button_data[selected_menu_num] == self.DONE:
            seed: Seed = SeedJar.transferIn(self.controller.pending_seed.seed())
            self.controller.pending_seed = None
            return Destination(SeedOptionsView, view_args={"seed": seed}, clear_history=True)


class SeedDiscardView(View):

    KEEP = ButtonData('Keep Seed')
    DISCARD = ButtonData.DISCARD

    def __init__(self, seed: Seed|None = None):
        super().__init__()
        self.seed: Seed = seed
        if self.seed is None:
            self.seed = self.controller.pending_seed.seed()  # TODO: check

    def run(self):
        button_data = [self.KEEP, self.DISCARD]
        selected_menu_num = self.run_screen(
            WarningScreen,
            title='Discard Seed?',
            status_headline=None,
            text=f'Wipe seed {self.seed.fingerprint} from the device?',
            show_back_button=False,
            button_data=button_data,
        )
        if button_data[selected_menu_num] == self.KEEP:
            # Use skip_current_view=True to prevent BACK from landing on this warning screen
            if self.seed is not None:
                return Destination(SeedOptionsView, view_args={'seed': self.seed}, skip_current_view=True)
            return Destination(SeedFinalizeView, skip_current_view=True)
        if button_data[selected_menu_num] == self.DISCARD:
            if self.seed is not None:
                SeedJar.remove(self.seed)
            else:
                self.controller.pending_seed = None
            return Destination(MainMenuView, clear_history=True)


class SeedOptionsView(View):
    '''
    Views for actions on individual seeds:
    '''

    SCAN = ButtonData('Scan for Seed').with_icon(IconConstants.SCAN)
    EXPORT_KEY_IMAGES = ButtonData('Export Key Images').with_icon(IconConstants.QRCODE)
    EXPLORER = ButtonData('Address Explorer')
    VIEW_ONLY_WALLET = ButtonData('View only Wallet').with_icon(IconConstants.QRCODE)
    VIEW_ONLY_WALLET_JSON = ButtonData('View only Wallet (json)').with_icon(IconConstants.QRCODE)
    BACKUP = ButtonData('Backup Seed').with_icon(FontAwesomeIconConstants.VAULT).with_right_icon(IconConstants.CHEVRON_RIGHT)
    CONVERT_POOLYSEED = ButtonData('To Monero seed').with_icon(IconConstants.CHEVRON_RIGHT)
    DISCARD = ButtonData.DISCARD.with_icon(FontAwesomeIconConstants.TRASH_CAN).with_icon_color(GUIConstants.RED)

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        from xmrsigner.views.monero_views import OverviewView
        if self.controller.transaction:
            #  TODO: before here was a check if seed address matchs transaction
            #        removed for now, but recheck if it was really necessary to
            #        check
            if self.controller.resume_main_flow and self.controller.resume_main_flow == Flow.TX:
                # Re-route us directly back to the start of the Tx flow
                self.controller.resume_main_flow = None
                return Destination(
                    OverviewView,
                    view_args={
                        'seed': self.seed
                    },
                    skip_current_view=True
                )
        button_data = []
        button_data.append(self.SCAN)
        button_data.append(self.EXPORT_KEY_IMAGES)
        if len(self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)) > 1:
            self.VIEW_ONLY_WALLET.with_right_icon(IconConstants.CHEVRON_RIGHT)
        button_data.append(self.VIEW_ONLY_WALLET)
        # button_data.append(self.VIEW_ONLY_WALLET_JSON)  # TODO: 2024-08-26, finish implementation
        button_data.append(self.BACKUP)
        if self.seed.type == SeedType.POLYSEED:
            button_data.append(self.CONVERT_POOLYSEED)
        button_data.append(self.DISCARD)
        selected_menu_num = self.run_screen(
            seed_screens.SeedOptionsScreen,
            button_data=button_data,
            fingerprint=self.seed.fingerprint,
            polyseed=self.seed.type == SeedType.POLYSEED,
            my_monero=self.seed.isLegacy
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Force BACK to always return to the Main Menu if in a flow
            return Destination(BackStackView if self.controller.resume_main_flow is None else MainMenuView)
        if button_data[selected_menu_num] == self.SCAN:
            from xmrsigner.views.scan_views import ScanUR2View
            return Destination(ScanUR2View)
        if button_data[selected_menu_num] == self.BACKUP:
            return Destination(SeedBackupView, view_args={"seed": self.seed})
        if button_data[selected_menu_num] == self.CONVERT_POOLYSEED:
            if self.seed.type == SeedType.POLYSEED:
                monero_seed = SeedJar.transferIn(self.seed.moneroSeed())
                SeedJar.remove(self.seed)
                return Destination(SeedOptionsView, view_args={"seed": monero_seed}, skip_current_view=True)
            self.run_screen(
                DireWarningScreen,
                title='Not a Polyseed',
                status_headline='Error!',
                text="Can't convert to monero seed!",
                show_back_button=False,
                button_data=['OK'],
            ).display()
            return Destination(BackStackView, skip_current_view=True)
        if button_data[selected_menu_num] == self.EXPORT_KEY_IMAGES:
            return Destination(ExportKeyImagesView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == self.VIEW_ONLY_WALLET:
            return Destination(WalletViewKeyQRView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == self.VIEW_ONLY_WALLET_JSON:
            return Destination(WalletViewKeyJsonQRView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView, view_args={"seed": self.seed})


class SeedBackupView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        VIEW_WORDS = ButtonData('View Seed Words').with_icon(FontAwesomeIconConstants.LIST)
        EXPORT_SEEDQR = ButtonData('Export as SeedQR').with_icon(FontAwesomeIconConstants.PEN)
        button_data = [VIEW_WORDS, EXPORT_SEEDQR]
        selected_menu_num = ButtonListScreen(
            title='Backup Seed',
            button_data=button_data,
            is_bottom_list=True,
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == EXPORT_SEEDQR:
            return Destination(SeedTranscribeSeedQRFormatView, view_args={'seed': self.seed})


"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):

    def __init__(self, seed: Seed|None = None):
        super().__init__()
        self.seed: Seed|None = seed

    def run(self):
        destination = Destination(
            SeedWordsView,
            view_args={'seed': self.seed, 'page_index': 0},
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(Setting.DIRE_WARNINGS) == Option.DISABLED:
            # Forward straight to showing the words
            return destination
        selected_menu_num = DireWarningScreen(
            text='''You must keep your seed words private & away from all online devices.''',
        ).display()
        if selected_menu_num == 0:
            # User clicked 'I Understand'
            return destination
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)


class SeedWordsView(View):

    def __init__(self, seed: Seed|None, passphrase: str|None = None, page_index: int = 0):
        super().__init__()
        self.seed: Seed|None = self.seed = self.controller.pending_seed.seed() if seed is None else seed
        self.pending_seed = self.controller.pending_seed
        wordlist_language: Language = self.settings.get_value(Setting.MONERO_WORDLIST_LANGUAGE if self.seed.type != SeedType.POLYSEED else Setting.POLYSEED_WORDLIST_LANGUAGE)
        self.passphrase: str = passphrase or ''
        if self.passphrase == '' and self.seed.type == SeedType.POLYSEED and self.pending_seed.password != '':
            self.passphrase = self.pending_seed.password
        self.page_index = page_index
        seed_word_count: int = 16 if self.seed.type == SeedType.POLYSEED else (13 if self.seed.isLegacy else 25)
        self.num_pages=int(ceil(seed_word_count/4))

    def run(self):
        NEXT = ButtonData.NEXT
        DONE = ButtonData.DONE
        # Slice the mnemonic to our current 4-word section
        words_per_page = 4
        mnemonic = self.seed.phrase(wordlist_language, self.passphrase).insecure().split()
        words = mnemonic[self.page_index * words_per_page:(self.page_index + 1) * words_per_page]
        button_data = []
        if self.page_index < self.num_pages - 1 or self.seed is None:
            button_data.append(NEXT)
        else:
            button_data.append(DONE)
        selected_menu_num = seed_screens.SeedWordsScreen(
            title=f"Seed Words: {self.page_index+1}/{self.num_pages}",
            words=words,
            page_index=self.page_index,
            num_pages=self.num_pages,
            button_data=button_data,
            words_per_page = words_per_page,
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == NEXT:
            if self.seed is None and self.page_index == self.num_pages - 1:
                return Destination(SeedWordsBackupTestPromptView, view_args={'seed': self.seed})
            return Destination(SeedWordsView, view_args={'seed': self.seed, 'page_index': self.page_index + 1})
        if button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(SeedWordsBackupTestPromptView, view_args={'seed': self.seed})


"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""
class SeedWordsBackupTestPromptView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        VERIFY = ButtonData('Verify')
        SKIP = ButtonData('Skip')
        button_data = [VERIFY, SKIP]
        selected_menu_num = seed_screens.SeedWordsBackupTestPromptScreen(
            button_data=button_data,
        ).display()
        if button_data[selected_menu_num] == VERIFY:
            return Destination(SeedWordsBackupTestView, view_args=dict(seed=self.seed))
        if button_data[selected_menu_num] == SKIP:
            if self.seed is not None:
                return Destination(SeedOptionsView, view_args=dict(seed=self.seed))
            return Destination(SeedFinalizeView)


class SeedWordsBackupTestView(View):

    def __init__(self, seed: Seed|None, confirmed_list: list[bool] = None, cur_index: int = None):
        super().__init__()
        self.seed = seed
        if self.seed is None:  # TODO: fix
            self.seed = self.controller.jar.get_pending_seed()
        self.mnemonic_list = self.seed.mnemonic_display_list
        self.confirmed_list = confirmed_list
        if not self.confirmed_list:
            self.confirmed_list = []
        self.cur_index = cur_index

    def run(self):
        if self.cur_index is None:
            self.cur_index = int(random() * len(self.mnemonic_list))
            while self.cur_index in self.confirmed_list:
                self.cur_index = int(random() * len(self.mnemonic_list))
        real_word = self.mnemonic_list[self.cur_index]
        button_data = [real_word]
        while len(button_data) < 4:
            new_word = choice(self.seed.get_wordlist(self.seed.wordlist_language_code))
            if new_word not in button_data:
                button_data.append(new_word)
        shuffle(button_data)
        selected_menu_num = ButtonListScreen(
            title=f"Verify Word #{self.cur_index + 1}",
            show_back_button=False,
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=True,
        ).display()
        if button_data[selected_menu_num] == real_word:
            self.confirmed_list.append(self.cur_index)
            if len(self.confirmed_list) == len(self.mnemonic_list):
                # Successfully confirmed the full mnemonic!
                return Destination(SeedWordsBackupTestSuccessView, view_args=dict(seed=self.seed))
            # Continue testing the remaining words
            return Destination(SeedWordsBackupTestView, view_args=dict(seed=self.seed, confirmed_list=self.confirmed_list))
        else:
            # Picked the WRONG WORD!
            return Destination(
                SeedWordsBackupTestMistakeView,
                view_args=dict(
                    seed=self.seed,
                    cur_index=self.cur_index,
                    wrong_word=button_data[selected_menu_num],
                    confirmed_list=self.confirmed_list,
                )
            )


class SeedWordsBackupTestMistakeView(View):

    def __init__(
            self,
            seed: Seed,
            cur_index: int,
            wrong_word: str,
            confirmed_list: list[bool] = None
    ):
        super().__init__()
        self.seed: Seed = seed
        self.cur_index = cur_index
        self.wrong_word = wrong_word
        self.confirmed_list = confirmed_list

    def run(self):
        REVIEW = ButtonData('Review Seed Words')
        RETRY = ButtonData('Try Again')
        button_data = [REVIEW, RETRY]
        selected_menu_num = DireWarningScreen(
            title='Verification Error',
            show_back_button=False,
            status_headline=f'Wrong Word!',
            text=f'Word #{self.cur_index + 1} is not "{self.wrong_word}"!',
            button_data=button_data,
        ).display()
        if button_data[selected_menu_num] == REVIEW:
            return Destination(SeedWordsView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == RETRY:
            return Destination(
                SeedWordsBackupTestView,
                view_args={
                    'seed': self.seed,
                    'confirmed_list': self.confirmed_list,
                    'cur_index': self.cur_index
                }
            )


class SeedWordsBackupTestSuccessView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        LargeIconStatusScreen(
            title='Backup Verified',
            show_back_button=False,
            status_headline='Success!',
            text='All mnemonic backup words were successfully verified!',
            button_data=[ButtonData.OK]
        ).display()
        if self.seed is not None:
            return Destination(SeedOptionsView, view_args=dict(seed=self.seed), clear_history=True)
        else:
            return Destination(SeedFinalizeView)


"""****************************************************************************
    Export as SeedQR
****************************************************************************"""
class SeedTranscribeSeedQRFormatView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed = seed

    def run(self):
        num_modules_standard = {
                (SeedType.MONERO, False): 29,
                (SeedType.MONERO, True): 25,
                (SeedType.POLYSEED, False): 25
            }[(seed.type, seed.isLegacy)]
        num_modules_compact = {
                (SeedType.MONERO, False): 25,
                (SeedType.MONERO, True): 21,
                (SeedType.POLYSEED, False): 25
            }[(seed.type, seed.isLegacy)]
        STANDARD = ButtonData(f'Standard: {num_modules_standard}x{num_modules_standard}')
        COMPACT = ButtonData(f'Compact: {num_modules_compact}x{num_modules_compact}')
        if self.settings.get_value(Setting.COMPACT_SEEDQR) != Option.ENABLED:
            # Only configured for standard SeedQR
            return Destination(
                SeedTranscribeSeedQRWarningView,
                view_args={
                    'seed': self.seed,
                    'seedqr_format': QrType.SEED_QR,
                    'num_modules': num_modules_standard,
                },
                skip_current_view=True,
            )
        button_data = [STANDARD, COMPACT]
        selected_menu_num = seed_screens.SeedTranscribeSeedQRFormatScreen(
            title='SeedQR Format',
            seed=self.seed,
            button_data=button_data,
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == STANDARD:
            seedqr_format = QrType.SEED_QR
            num_modules = num_modules_standard
        else:
            seedqr_format = QrType.COMPACT_SEED_QR
            num_modules = num_modules_compact
        return Destination(
            SeedTranscribeSeedQRWarningView,
                view_args={
                    'seed': self.seed,
                    'seedqr_format': seedqr_format,
                    'num_modules': num_modules,
                }
            )


class SeedTranscribeSeedQRWarningView(View):

    def __init__(self, seed: Seed, seedqr_format: QrType = QrType.SEED_QR, num_modules: int = 29):
        super().__init__()
        self.seed: Seed = seed
        self.seedqr_format: QrType = seedqr_format
        self.num_modules = num_modules

    def run(self):
        destination = Destination(
            SeedTranscribeSeedQRWholeQRView,
            view_args={
                'seed': self.seed,
                'seedqr_format': self.seedqr_format,
                'num_modules': self.num_modules,
            },
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(Setting.DIRE_WARNINGS) == Option.DISABLED:
            # Forward straight to transcribing the SeedQR
            return destination
        selected_menu_num = DireWarningScreen(
                status_headline='SeedQR is your private key!',
            text='''Never photograph it or scan it into an online device.''',
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        # User clicked 'I Understand'
        return destination


class SeedTranscribeSeedQRWholeQRView(View):

    def __init__(self, seed: Seed, seedqr_format: str, num_modules: int):
        super().__init__()
        self.seedqr_format: QrType = seedqr_format
        self.num_modules = num_modules
        self.seed: Seed = seed

    def run(self):
        e = SeedQrEncoder(self.seed.mnemonic_list, self.seed.wordlist) if self.seedqr_format == QrType.SEED_QR else CompactSeedQrEncoder(self.seed.mnemonic_list, self.seed.wordlist)
        ret = seed_screens.SeedTranscribeSeedQRWholeQRScreen(
            qr_data=e.next_part(),
            num_modules=self.num_modules,
        ).display()
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        return Destination(
            SeedTranscribeSeedQRZoomedInView,
            view_args={
                'seed': self.seed,
                'seedqr_format': self.seedqr_format
            }
        )


class SeedTranscribeSeedQRZoomedInView(View):

    def __init__(self, seed: Seed, seedqr_format: QrType):
        super().__init__()
        self.seedqr_format: QrType = seedqr_format
        self.seed: Seed = seed

    def run(self):
        if self.seedqr_format == QrType.SEED_QR:
            num_modules = 29 if (len(self.mnemonic_list) * 4) > 77 else 25  # Version 1 can fit 77 numeric digits into 25x25 and up to 127 numeric digits into 29x29
        elif self.seedqr_format == QrType.COMPACT_SEED_QR:
            num_modules = 25 if ceil(len(self.mnemonic_list) * 11 / 8) > 32 else 21  # Version 1 can fit 17 bytes into 21x21 and up to 32 bytes into 25x25
        e = SeedQrEncoder(self.seed.mnemonic_list, self.seed.wordlist) if self.seedqr_format == QrType.SEED_QR else CompactSeedQrEncoder(self.seed.mnemonic_list, self.seed.wordlist)
        seed_screens.SeedTranscribeSeedQRZoomedInScreen(
            qr_data=e.next_part(),
            num_modules=num_modules,
        ).display()
        return Destination(SeedTranscribeSeedQRConfirmQRPromptView, view_args={'seed': self.seed})


class SeedTranscribeSeedQRConfirmQRPromptView(View):
    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        SCAN = ButtonData('Confirm SeedQR').with_icon(FontAwesomeIconConstants.QRCODE)
        DONE = ButtonData.DONE
        button_data = [SCAN, DONE]
        selected_menu_option = seed_screens.SeedTranscribeSeedQRConfirmQRPromptScreen(
            title='Confirm SeedQR?',
            button_data=button_data,
        ).display()
        if selected_menu_option == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_option] == SCAN:
            return Destination(SeedTranscribeSeedQRConfirmScanView, view_args={'seed': self.seed})
        if button_data[selected_menu_option] == DONE:
            return Destination(SeedOptionsView, view_args={'seed': self.seed}, clear_history=True)


class SeedTranscribeSeedQRConfirmScanView(View):
    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        from xmrsigner.gui.screens.scan_screens import ScanScreen
        # Run the live preview and QR code capture process
        wordlist_language: Language = self.settings.get_value(Setting.MONERO_WORDLIST_LANGUAGE if self.seed.type != SeedType.POLYSEED else Setting.POLYSEED_WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language)
        ScanScreen(decoder=self.decoder, instructions_text="Scan your SeedQR").display()
        if self.decoder.is_complete:
            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()
                # Found a valid mnemonic seed! But does it match?
                if seed_mnemonic != self.seed.mnemonic_list:
                    DireWarningScreen(
                        title="Confirm SeedQR",
                        status_headline="Error!",
                        text="Your transcribed SeedQR does not match your original seed!",
                        show_back_button=False,
                        button_data=["Review SeedQR"],
                    ).display()
                    return Destination(BackStackView, skip_current_view=True)
                LargeIconStatusScreen(
                    title="Confirm SeedQR",
                    status_headline="Success!",
                    text="Your transcribed SeedQR successfully scanned and yielded the same seed.",
                    show_back_button=False,
                    button_data=["OK"],
                ).display()
                return Destination(SeedOptionsView, view_args={"seed": self.seed})
            # Will this case ever happen? Will trigger if a different kind of QR code is scanned
            DireWarningScreen(
                title="Confirm SeedQR",
                status_headline="Error!",
                text="Your transcribed SeedQR could not be read!",
                show_back_button=False,
                button_data=["Review SeedQR"],
            ).display()
            return Destination(BackStackView, skip_current_view=True)
