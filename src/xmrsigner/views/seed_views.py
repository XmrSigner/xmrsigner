from ots.seed import (
    Seed,
    SeedIndices,
    Polyseed,
    MoneroSeed,
    LegacySeed,
    SeedLanguage,
    Network,
    SeedType
)
from ots.seed_jar import SeedJar
from ots.exceptions import (
    OtsPolyseedNoPasswordProvidedException,
    OtsPolyseedChecksumMismatchException,
    OtsSeedSeedDecodingFailedException
)

from random import (
    random,
    shuffle,
    choice
)
from math import ceil

from xmrsigner.controller import Controller, Flow
from xmrsigner.gui.components import (
    Theme,
    FontAwesome,
    IconConstants
)
from xmrsigner.gui.button_data import (
    ButtonData,
    FingerprintButtonData
)
from xmrsigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    LargeIconStatusScreen,
    WarningScreen,
    DireWarningScreen,
    seed_screens,
    QRDisplayScreen
)
from xmrsigner.gui.screens.monero_screens import DateOrBlockHeightScreen
from xmrsigner.models.decode_qr import DecodeQR
from xmrsigner.models.monero_encoder import (
    MoneroKeyImageQrEncoder,
    ViewOnlyWalletQrEncoder,
    ViewOnlyWalletJsonQrEncoder
)
from xmrsigner.models.seed_encoder import (
    SeedQrEncoder,
    CompactSeedQrEncoder
)
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.pending_seed import (
    PendingSeed,
    PendingSeedPhrase,
    PendingSeedIndices
)
from xmrsigner.models.settings import (
    Settings,
    Setting
)
from xmrsigner.models.settings_definition import Network as NetworkChoice
from xmrsigner.models.settings_definition import (
    SettingsDefinition,
    ViewOnlyWalletFormat,
    Option
)
from xmrsigner.models.threads import BaseThread, ThreadsafeCounter
from xmrsigner.models.wordlists import words
from xmrsigner.views.view import (
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
            FingerprintButtonData(
                seed.fingerprint,
                seed.type == SeedType.POLYSEED,
                seed.is_legacy
            )
            for seed in SeedJar.items()
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
    TYPE_13WORD = ButtonData('Enter 13-word seed').with_icon(FontAwesome.KEYBOARD)
    TYPE_25WORD = ButtonData('Enter 25-word seed').with_icon(FontAwesome.KEYBOARD)
    TYPE_POLYSEED = ButtonData('Enter Polyseed').with_icon(FontAwesome.KEYBOARD)
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
        if button_data[selected_menu_num] == self.CREATE:
            from .tools_views import ToolsCreateSeedTypeView
            return Destination(ToolsCreateSeedTypeView)
        if button_data[selected_menu_num] == self.TYPE_13WORD:
            self.controller.pending_seed = PendingSeedPhrase(isLegacy=True)
        if button_data[selected_menu_num] == self.TYPE_25WORD:
            self.controller.pending_seed = PendingSeedPhrase()
        if button_data[selected_menu_num] == self.TYPE_POLYSEED:
            self.controller.pending_seed = PendingSeedPhrase(type=SeedType.POLYSEED)
        if self.controller.pending_seed is not None:
            return Destination(SeedNetworkView)


class SeedNetworkView(View):

    def run(self):
        networks: list[NetworkChoice] = self.settings.get_value(Setting.NETWORKS)
        if len(networks) == 1:
            self.controller.pending_seed.network = networks[0].value
            return Destination(SeedBlockHeightView)
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
        self.controller.pending_seed.network = networks[selected_menu_num].value
        return Destination(SeedBlockHeightView)


class SeedBlockHeightView(View):

    def __init__(self):
        super().__init__()
        self.pending_seed: PendingSeed = self.controller.pending_seed

    def run(self):
        if self.pending_seed.type == SeedType.POLYSEED or self.pending_seed.height is not None:
            return Destination(SeedMnemonicEntryView)
        ret = self.run_screen(
            DateOrBlockHeightScreen,
            network = self.pending_seed.network
        )
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if type(ret) == str:
            self.pending_seed.height = int(ret)
        return Destination(SeedMnemonicEntryView)


class SeedMnemonicEntryView(View):

    def __init__(
        self,
        cur_word_index: int = 0,
        is_calc_final_word: bool=False
    ):
        super().__init__()
        self.cur_word_index: int = cur_word_index
        if self.controller.pending_seed.pre_filled:
            self.cur_word_index = self.controller.pending_seed.length - 1
        self.cur_word: str = self.controller.pending_seed.get(cur_word_index)
        self.is_calc_final_word: bool = is_calc_final_word

    def run(self):
        print(f'cur_word: {type(self.cur_word)}')
        if not self.controller.pending_seed.pre_filled:
            ret = self.run_screen(
                seed_screens.SeedMnemonicEntryScreen,
                title=f'Seed Word #{self.cur_word_index + 1}',  # Human-readable 1-indexing!
                initial_letters=list(self.cur_word) if len(self.cur_word) > 0 else ['a'],
                wordlist=words(
                    self.controller.pending_seed.type,
                    self.settings.get_value(
                        Setting.POLYSEED_WORDLIST_LANGUAGE if self.controller.pending_seed.type == SeedType.POLYSEED else Setting.MONERO_WORDLIST_LANGUAGE
                    ).value
                ),
            )
            if ret == RET_CODE__BACK_BUTTON:
                if self.cur_word_index > 0:
                    return Destination(BackStackView)
                self.controller.pending_seed = None
                return Destination(MainMenuView)
            # ret will be our new mnemonic word
            self.controller.pending_seed.set(ret, self.cur_word_index)
            if (  # TODO: really? Think that is to remove...
                self.controller.pending_seed.type != SeedType.POLYSEED
                and self.is_calc_final_word
                and self.cur_word_index == (self.controller.pending_seed.length - 2)
            ):
                print('DEAD CODE???')
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
        self.controller.pending_seed.pre_filled = False
        # Attempt to finalize the mnemonic
        try:
            self.controller.pending_seed.seed()
        except OtsPolyseedNoPasswordProvidedException:
            return Destination(PolyseedPasswordView)
        except OtsPolyseedChecksumMismatchException:
            return Destination(SeedMnemonicInvalidView)
        except OtsSeedSeedDecodingFailedException:
            return Destination(SeedMnemonicInvalidView)
        except Exception as e:
            print(f'error: {e}')
            raise e
            # should never happen
            self.controller.pending_seed = None
            return Destination(MainMenuView)
        return Destination(SeedFinalizeView)


class SeedMnemonicInvalidView(View):

    EDIT = ButtonData('Review & Edit')
    DISCARD = ButtonData.DISCARD()

    def __init__(self):
        super().__init__()

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
                SeedMnemonicEntryView,
                view_args={"cur_word_index": 0}
            )
        if button_data[selected_menu_num] == self.DISCARD:
            self.controller.pending_seed = None
            return Destination(MainMenuView)


class SeedFinalizeView(View):

    FINALIZE = ButtonData('Done')
    PASSPHRASE = ButtonData('Add Passphrase').with_icon(FontAwesome.LOCK)

    def __init__(self):
        super().__init__()
        self.pending_seed: PendingSeed = self.controller.pending_seed

    def run(self):
        option: Option = self.settings.get_value(Setting.POLYSEED_PASSPHRASE if self.pending_seed.type == SeedType.POLYSEED else Setting.MONERO_SEED_PASSPHRASE)
        if option == Option.DISABLED or self.pending_seed.isLegacy or self.pending_seed.passphrase != '':
            seed = SeedJar.transferIn(self.controller.pending_seed.seed(), str(SeedJar.count() + 1))
            self.controller.pending_seed = None
            return Destination(SeedOptionsView, view_args={'seed': seed}, clear_history=True)
        if option == Option.REQUIRED and self.pending_seed.passphrase == '':
            return Destination(SeedAddPassphraseView)
        if option == Option.ENABLED and self.pending_seed.passphrase == '':
            button_data = [
                self.FINALIZE,
                self.PASSPHRASE
            ]
            selected_menu_num = self.run_screen(
                seed_screens.SeedFinalizeScreen,
                fingerprint=self.pending_seed.seed().fingerprint,
                polyseed=self.pending_seed.type == SeedType.POLYSEED,
                button_data=button_data,
            )
            if button_data[selected_menu_num] == self.FINALIZE:
                seed = SeedJar.transferIn(self.controller.pending_seed.seed(), str(SeedJar.count() + 1))
                self.controller.pending_seed = None
                return Destination(SeedOptionsView, view_args={'seed': seed}, clear_history=True)
            if button_data[selected_menu_num] == self.PASSPHRASE:
                return Destination(SeedAddPassphraseView)


class PolyseedPasswordView(View):

    def __init__(self):
        super().__init__()
        self.pending_seed = self.controller.pending_seed

    def run(self):
        ret = self.run_screen(
            seed_screens.SeedAddPassphraseScreen,
            passphrase=self.pending_seed.passphrase,
            title='Password required'
        )
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        # The new passphrase will be the return value; it might be empty.
        self.pending_seed.password = ret
        if len(self.pending_seed.password) > 0:
            return Destination(PolyseedReviewPasswordView)
        return Destination(PolyseedPasswordView)  # TODO: Warning screen: "password required!?


class PolyseedReviewPasswordView(View):
    '''
    Display the completed password back to the user.
    '''

    EDIT = ButtonData('Edit password')
    DONE = ButtonData('Done')

    def __init__(self):
        super().__init__()
        self.pending_seed = self.controller.pending_seed

    def run(self):
        # Get the before/after fingerprints
        fingerprint = self.pending_seed.seed().fingerprint
        button_data = [self.EDIT, self.DONE]
        # Because we have an explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = self.run_screen(
            seed_screens.PolyseedReviewPasswordScreen,
            fingerprint=self.pending_seed.seed().fingerprint,
            password=self.pending_seed.password,
            button_data=button_data,
            show_back_button=False,
        )
        if button_data[selected_menu_num] == self.EDIT:
            return Destination(PolyseedPasswordView)
        if button_data[selected_menu_num] == self.DONE:
            return Destination(SeedFinalizeView)


class SeedAddPassphraseView(View):

    def __init__(self):
        super().__init__()
        self.pending_seed = self.controller.pending_seed

    def run(self):
        ret = self.run_screen(
            seed_screens.SeedAddPassphraseScreen,
            passphrase=self.pending_seed.passphrase
        )
        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        # The new passphrase will be the return value; it might be empty.
        self.pending_seed.passphrase = ret
        print(f'passphrase: "{self.pending_seed.passphrase}"({type(self.pending_seed.passphrase)})')
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
        self.pending_seed.passphrase = ''
        fingerprint_without = self.pending_seed.seed().fingerprint
        self.pending_seed.passphrase = passphrase
        button_data = [self.EDIT, self.DONE]
        # Because we have an explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = self.run_screen(
            seed_screens.SeedReviewPassphraseScreen,
            fingerprint_without=fingerprint_without,
            fingerprint_with=fingerprint_with,
            passphrase=self.pending_seed.passphrase,
            polyseed=self.pending_seed.type == SeedType.POLYSEED,
            is_legacy=self.pending_seed.isLegacy,
            button_data=button_data,
            show_back_button=False,
        )
        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)
        if button_data[selected_menu_num] == self.DONE:
            seed: Seed = SeedJar.transferIn(self.controller.pending_seed.seed(), str(SeedJar.count() + 1))
            self.controller.pending_seed = None
            return Destination(SeedOptionsView, view_args={"seed": seed}, clear_history=True)


class SeedDiscardView(View):

    KEEP = ButtonData('Keep Seed')
    DISCARD = ButtonData.DISCARD()

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
                return Destination(
                    SeedOptionsView,
                    view_args={
                        'seed': self.seed
                    },
                    skip_current_view=True
                )
            return Destination(SeedFinalizeView, skip_current_view=True)
        if button_data[selected_menu_num] == self.DISCARD:
            if self.seed is not None:
                SeedJar.remove(self.seed)
            else:
                self.controller.pending_seed = None
            return Destination(MainMenuView, clear_history=True)


class ExportKeyImagesView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        try:
            key_image = self.seed.wallet.exportKeyImages()
        except Exception as e:
            print(e)
            raise e
            self.run_screen(WarningScreen, title='Key Images Export', text='Error on exporting key images from the wallet', status_headline='Failed!', status_color='red')
            return Destination(BackStackView)
        try:
            self.run_screen(
                QRDisplayScreen,
                qr_encoder=MoneroKeyImageQrEncoder(key_image, self.controller.settings.get_value(Setting.QR_DENSITY))
            )
        except Exception as e:
            raise e
            self.run_screen(WarningScreen, title='Key Images Export', text='Error on exporting key images from the wallet', status_headline='Failed!', status_color='red')
            return Destination(BackStackView)
        return Destination(MainMenuView)


class NoOutputsImportedView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        self.run_screen(
            LargeIconStatusScreen,
            title='Load Outputs',
            text=f"Wallet {self.seed.fingerprint} has not received funds yet.",
            status_headline='No balance found!'
        )
        return Destination(MainMenuView)  # TODO: 2024-07-27, thought: ask user if he wants to see the address explorer to tranfer funds to the wallet


class ImportOutputsView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.loading_screen = None
        self.seed: Seed = seed
        from xmrsigner.gui.screens.screen import LoadingScreenThread
        self.loading_screen = LoadingScreenThread(text=f'Loading Outputs for {self.seed.fingerprint}...')
        self.loading_screen.start()

    def run(self):
        try:
            num_imported = self.seed.importOutputs(self.controller.outputs)
            if int(num_imported) == 0:  # we have a zero balance
                if self.loading_screen:
                    self.loading_screen.stop()
                return Destination(
                    NoOutputsImportedView,
                    view_args={
                        'seed': self.seed
                    }
                )
            if self.loading_screen:
                self.loading_screen.stop()
            self.run_screen(LargeIconStatusScreen, title='Loaded Outputs', text=f"Loaded {num_imported} outputs for {self.seed.fingerprint} into wallet.", status_headline='Success!')
            return Destination(ExportKeyImagesView, view_args={'seed': self.seed})
        except Exception as e:
            print(e)
        if self.loading_screen:
            self.loading_screen.stop()
        self.run_screen(WarningScreen, title='Import outputs', text=f'Error on importing outputs into wallet {self.seed.fingerprint}', status_headline='Failed!', status_color='red')
        return Destination(MainMenuView)


class WalletViewKeyQRView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        wallet_qr_format: ViewOnlyWalletFormat|None = None
        wallet_qr_format_settings: list[ViewOnlyWalletFormat] = self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)
        if len(wallet_qr_format_settings) == 0:
            wallet_qr_format_settings = ViewOnlyWalletFormat.all()
        if len(wallet_qr_format_settings) > 1:
            ret = self.run_screen(
                    ButtonListScreen,
                    title=SettingsDefinition.get_settings_entry(Setting.VIEW_WALLET_QR_FORMAT).display_name,
                    button_data=[ButtonData(format.display) for format in wallet_qr_format_settings]
            )
            if ret == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            wallet_qr_format: ViewOnlyWalletFormat = wallet_qr_format_settings[ret]
        else:
            wallet_qr_format: ViewOnlyWalletFormat = wallet_qr_format_settings[0]
        if wallet_qr_format == ViewOnlyWalletFormat.WALLET_URI:
            self.run_screen(
                QRDisplayScreen,
                qr_encoder=ViewOnlyWalletQrEncoder(self.seed)
            )
            return Destination(BackStackView)
        if wallet_qr_format == ViewOnlyWalletFormat.JSON:
            self.run_screen(
                QRDisplayScreen,
                qr_encoder=ViewOnlyWalletJsonQrEncoder(self.seed)
            )
            return Destination(BackStackView)


class SeedOptionsView(View):
    '''
    Views for actions on individual seeds:
    '''

    SCAN = ButtonData('Scan for Seed').with_icon(IconConstants.SCAN)
    EXPORT_KEY_IMAGES = ButtonData('Export Key Images').with_icon(IconConstants.QRCODE)
    EXPLORER = ButtonData('Address Explorer').with_icon(FontAwesome.LIST)
    ADDRESS = ButtonData('Verify address').with_icon(IconConstants.SCAN)
    VIEW_ONLY_WALLET = ButtonData('View only Wallet').with_icon(IconConstants.QRCODE)
    VIEW_ONLY_WALLET_SELECT = ButtonData('View only Wallet').with_right_icon(IconConstants.CHEVRON_RIGHT)
    BACKUP = ButtonData('Backup Seed').with_icon(FontAwesome.VAULT).with_right_icon(IconConstants.CHEVRON_RIGHT)
    CONVERT_POOLYSEED = ButtonData('To Monero seed').with_icon(IconConstants.CHEVRON_RIGHT)
    DISCARD = ButtonData.DISCARD().with_icon(FontAwesome.TRASH_CAN).with_icon_color(Theme.DISCARD_COLOR)

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
        button_data.append(self.EXPLORER)
        button_data.append(self.ADDRESS)
        button_data.append(self.EXPORT_KEY_IMAGES)
        button_data.append(
            self.VIEW_ONLY_WALLET_SELECT if len(self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)) != 1 else self.VIEW_ONLY_WALLET
        )
        button_data.append(self.BACKUP)
        if self.seed.type == SeedType.POLYSEED:
            button_data.append(self.CONVERT_POOLYSEED)
        button_data.append(self.DISCARD)
        selected_menu_num = self.run_screen(
            seed_screens.SeedOptionsScreen,
            button_data=button_data,
            fingerprint=self.seed.fingerprint,
            polyseed=self.seed.type == SeedType.POLYSEED,
            is_legacy=self.seed.isLegacy
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # Force BACK to always return to the Main Menu if in a flow
            return Destination(BackStackView if self.controller.resume_main_flow is None else MainMenuView)
        if button_data[selected_menu_num] == self.SCAN:
            from xmrsigner.views.scan_views import ScanUR2View
            return Destination(ScanUR2View)
        if button_data[selected_menu_num] == self.EXPLORER:
            from xmrsigner.views.tools_views import ToolsAddressExplorerSeedAccountsView
            return Destination(
                ToolsAddressExplorerSeedAccountsView,
                view_args={
                    'seed': self.seed
                }
            )
        if button_data[selected_menu_num] == self.ADDRESS:
            self.controller.selected_seed = self.seed
            from xmrsigner.views.scan_views import ScanAddressView
            return Destination(ScanAddressView)
        if button_data[selected_menu_num] == self.BACKUP:
            return Destination(SeedBackupView, view_args={"seed": self.seed})
        if button_data[selected_menu_num] == self.CONVERT_POOLYSEED:
            if self.seed.type == SeedType.POLYSEED:
                print('convert {self.seed}({type(self.seed)}')
                monero_seed = SeedJar.transferIn(self.seed.moneroSeed(), str(SeedJar.count() + 1))
                print('remove')
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
        if button_data[selected_menu_num] in [self.VIEW_ONLY_WALLET, self.VIEW_ONLY_WALLET_SELECT]:
            return Destination(WalletViewKeyQRView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView, view_args={"seed": self.seed})


class SeedBackupView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        VIEW_WORDS = ButtonData('View Seed Words').with_icon(FontAwesome.LIST)
        EXPORT_SEEDQR = ButtonData('Export as SeedQR').with_icon(FontAwesome.PEN)
        button_data = [VIEW_WORDS, EXPORT_SEEDQR]
        selected_menu_num = ButtonListScreen(
            title='Backup Seed',
            button_data=button_data,
            is_bottom_list=True,
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == VIEW_WORDS:
            return Destination(
                SeedWordsWarningView,
                view_args={
                    'seed': self.seed
                }
            )
        if button_data[selected_menu_num] == EXPORT_SEEDQR:
            return Destination(
                SeedTranscribeSeedQRFormatView,
                view_args={
                    'seed': self.seed
                }
            )


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
            view_args={
                'seed': self.seed,
                'page_index': 0
            },
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

    def __init__(
            self,
            seed: Seed|None,
            password: str|None = None,
            passphrase: str|None = None,
            page_index: int = 0
    ):
        super().__init__()
        self.seed: Seed|None = self.controller.pending_seed.seed() if seed is None else seed
        self.pending_seed = self.controller.pending_seed
        self.wordlist_language: Language = self.settings.get_value(Setting.MONERO_WORDLIST_LANGUAGE if self.seed.type != SeedType.POLYSEED else Setting.POLYSEED_WORDLIST_LANGUAGE)
        self.password: str = password or ''
        self.passphrase: str = passphrase or ''
        if (
            self.passphrase == ''
            and self.seed.type == SeedType.POLYSEED
            and self.pending_seed is not None
            and self.pending_seed.password != ''
        ):
            self.passphrase = self.pending_seed.password
        self.page_index = page_index
        seed_word_count: int = 16 if self.seed.type == SeedType.POLYSEED else (13 if self.seed.isLegacy else 25)
        self.num_pages=int(ceil(seed_word_count/4))

    def run(self):
        NEXT = ButtonData.NEXT()
        DONE = ButtonData.DONE()
        # Slice the mnemonic to our current 4-word section
        words_per_page = 4
        mnemonic = self.seed.phrase(
            SeedLanguage.fromCode(self.wordlist_language.value),
            self.passphrase
        ).insecure().split()
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
                return Destination(
                    SeedWordsBackupTestPromptView,
                    view_args={
                        'seed': self.seed,
                        'password': self.controller.pending_seed.password,
                        'passphrase': self.controller.pending_seed.passphrase
                    }
                )
            return Destination(
                SeedWordsView,
                view_args={
                    'seed': self.seed,
                    'page_index': self.page_index + 1
                }
            )
        if button_data[selected_menu_num] == DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args={
                    'seed': self.seed,
                    'password': self.password,
                    'passphrase': self.passphrase
                }
            )


"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""
class SeedWordsBackupTestPromptView(View):

    def __init__(
        self,
        seed: Seed,
        password: str = '',
        passphrase: str = ''
    ):
        super().__init__()
        self.seed: Seed = seed
        self.password: str = password
        self.passphrase: str = passphrase

    def run(self):
        VERIFY = ButtonData('Verify')
        SKIP = ButtonData('Skip')
        button_data = [VERIFY, SKIP]
        selected_menu_num = seed_screens.SeedWordsBackupTestPromptScreen(
            button_data=button_data,
        ).display()
        if button_data[selected_menu_num] == VERIFY:
            return Destination(
                SeedWordsBackupTestView,
                view_args={
                    'seed': self.seed
                }
            )
        if button_data[selected_menu_num] == SKIP:
            if self.seed is not None:
                seed: Seed = SeedJar.transferIn(self.seed, str(SeedJar.count() + 1))
                return Destination(
                    SeedOptionsView,
                    view_args={
                        'seed': seed
                    },
                    clear_history=True
                )
            return Destination(SeedFinalizeView)


class SeedWordsBackupTestView(View):

    def __init__(
            self,
            seed: Seed|None,
            confirmed_list: list[bool]|None = None,
            cur_index: int = None,
            password: str = '',
            passphrase: str = ''
    ):
        super().__init__()
        self.seed: Seed|None = seed
        self.password: str = password
        self.passphrase: str = passphrase
        if self.seed is None:
            self.seed = self.controller.pending_seed.seed()
        self.wordlist_language: Language = self.settings.get_value(Setting.MONERO_WORDLIST_LANGUAGE if self.seed.type != SeedType.POLYSEED else Setting.POLYSEED_WORDLIST_LANGUAGE)
        self.mnemonic_list: list[str] = self.seed.phrase(
            SeedLanguage.fromCode(self.wordlist_language.value),
            self.password if self.seed.type == SeedType.POLYSEED else self.passphrase
        ).insecure().split()
        self.confirmed_list = confirmed_list or []
        self.cur_index = cur_index

    def run(self):
        if self.cur_index is None:
            self.cur_index = int(random() * len(self.mnemonic_list))
            while self.cur_index in self.confirmed_list:
                self.cur_index = int(random() * len(self.mnemonic_list))
        real_word = self.mnemonic_list[self.cur_index]
        button_data = [real_word]
        while len(button_data) < 4:
            new_word = choice(words(
                self.seed.type,
                SeedLanguage.fromCode(self.wordlist_language.value)
            ))
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
                return Destination(
                    SeedWordsBackupTestSuccessView,
                    view_args={
                        'seed': self.seed
                    }
                )
            # Continue testing the remaining words
            return Destination(
                SeedWordsBackupTestView,
                view_args={
                    'seed': self.seed,
                    'password': self.password,
                    'passphrase': self.passphrase,
                    'confirmed_list': self.confirmed_list
                }
            )
        else:
            # Picked the WRONG WORD!
            return Destination(
                SeedWordsBackupTestMistakeView,
                view_args={
                    'seed': self.seed,
                    'password': self.password,
                    'passphrase': self.passphrase,
                    'cur_index': self.cur_index,
                    'wrong_word': button_data[selected_menu_num],
                    'confirmed_list': self.confirmed_list
                }
            )


class SeedWordsBackupTestMistakeView(View):

    def __init__(
            self,
            seed: Seed,
            cur_index: int,
            wrong_word: str,
            password: str,
            passphrase: str,
            confirmed_list: list[bool]|None = None
    ):
        super().__init__()
        self.seed: Seed = seed
        self.password: str = password
        self.passphrase: str = passphrase
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
            return Destination(
                SeedWordsView,
                view_args={
                    'seed': self.seed
                }
            )
        if button_data[selected_menu_num] == RETRY:
            return Destination(
                SeedWordsBackupTestView,
                view_args={
                    'seed': self.seed,
                    'password': self.password,
                    'passphrase': self.passphrase,
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
            button_data=[ButtonData.OK()]
        ).display()
        if self.seed is not None:
            seed: Seed = SeedJar.transferIn(self.seed, str(SeedJar.count() + 1))
            return Destination(
                SeedOptionsView,
                view_args={
                    'seed': seed
                },
                clear_history=True
            )
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
            }[(self.seed.type, self.seed.isLegacy)]
        num_modules_compact = {
                (SeedType.MONERO, False): 25,
                (SeedType.MONERO, True): 21,
                (SeedType.POLYSEED, False): 25
            }[(self.seed.type, self.seed.isLegacy)]
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

    def __init__(
        self,
        seed: Seed,
        seedqr_format: QrType = QrType.SEED_QR,
        num_modules: int = 29
    ):
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
            text='Never photograph it or scan it into an online device.',
        ).display()
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        # User clicked 'I Understand'
        return destination


class SeedTranscribeSeedQRWholeQRView(View):

    def __init__(
        self,
        seed: Seed,
        seedqr_format: str,
        num_modules: int,
        password: str|None = None,
        passphrase: str|None = None,
    ):
        super().__init__()
        self.seedqr_format: QrType = seedqr_format
        self.num_modules: int = num_modules
        self.seed: Seed = seed
        self.password: str = password or ''
        self.passphrase: str = passphrase or ''
        self.indices: SeedIndices = seed.indices(password=self.password)

    def run(self):
        print(f'seed indices: {self.indices.values}')
        e = SeedQrEncoder(self.indices) if self.seedqr_format == QrType.SEED_QR else CompactSeedQrEncoder(self.indices)
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
                'indices': self.indices,
                'password': self.password,
                'passphrase': self.passphrase,
                'seedqr_format': self.seedqr_format
            }
        )


class SeedTranscribeSeedQRZoomedInView(View):

    def __init__(
        self,
        seed: Seed,
        indices: SeedIndices,
        password: str,
        passphrase: str,
        seedqr_format: QrType
    ):
        super().__init__()
        self.seedqr_format: QrType = seedqr_format
        self.seed: Seed = seed
        self.indices: SeedIndices = indices
        self.password: str = password
        self.passphrase: str = passphrase

    def run(self):
        if self.seedqr_format == QrType.SEED_QR:
            num_modules = 29 if (len(self.indices.values) * 4) > 77 else 25  # Version 1 can fit 77 numeric digits into 25x25 and up to 127 numeric digits into 29x29
        elif self.seedqr_format == QrType.COMPACT_SEED_QR:
            num_modules = 25 if ceil(len(self.indices.values) * 11 / 8) > 32 else 21  # Version 1 can fit 17 bytes into 21x21 and up to 32 bytes into 25x25
        e = SeedQrEncoder(self.indices) if self.seedqr_format == QrType.SEED_QR else CompactSeedQrEncoder(self.indices)
        seed_screens.SeedTranscribeSeedQRZoomedInScreen(
            qr_data=e.next_part(),
            num_modules=num_modules,
        ).display()
        return Destination(
            SeedTranscribeSeedQRConfirmQRPromptView,
            view_args={
                'seed': self.seed,
                'password': self.password,
                'passphrase': self.passphrase
            }
        )


class SeedTranscribeSeedQRConfirmQRPromptView(View):
    def __init__(
        self,
        seed: Seed,
        password: str,
        passphrase: str
    ):
        super().__init__()
        self.seed: Seed = seed
        self.password: str = password
        self.passphrase: str = passphrase

    def run(self):
        SCAN = ButtonData('Confirm SeedQR').with_icon(FontAwesome.QRCODE)
        DONE = ButtonData.DONE()
        button_data = [SCAN, DONE]
        selected_menu_option = seed_screens.SeedTranscribeSeedQRConfirmQRPromptScreen(
            title='Confirm SeedQR?',
            button_data=button_data,
        ).display()
        if selected_menu_option == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_option] == SCAN:
            return Destination(
                SeedTranscribeSeedQRConfirmScanView,
                view_args={
                    'seed': self.seed,
                    'password': self.password,
                    'passphrase': self.passphrase
                }
            )
        if button_data[selected_menu_option] == DONE:
            return Destination(
                SeedOptionsView,
                view_args={
                    'seed': self.seed
                },
                clear_history=True
            )


class SeedTranscribeSeedQRConfirmScanView(View):
    def __init__(
        self,
        seed: Seed,
        password: str,
        passphrase: str
    ):
        super().__init__()
        self.seed: Seed = seed
        self.password: str = password
        self.passphrase: str = passphrase

    def run(self):
        from xmrsigner.gui.screens.scan_screens import ScanScreen
        # Run the live preview and QR code capture process
        # self.decoder = DecodeQR()
        self.decoder = DecodeQR()
        ScanScreen(
            decoder=self.decoder,
            instructions_text='Scan your SeedQR'
        ).display()
        print(f'decoder: {self.decoder}')
        if self.decoder.is_complete:
            if self.decoder.is_seed:
                print(f'indices: {self.decoder.get_seed_indices()}')
                if self.seed.type == SeedType.POLYSEED:
                    seed2: Seed = Polyseed.decodeIndices(
                        self.decoder.get_seed_indices(),
                        network=self.seed.network,
                        password=self.password,
                        passphrase=self.passphrase
                    )
                if self.seed.type == SeedType.MONERO and not seed.isLegacy:
                    seed2: Seed = MoneroSeed.decodeIndices(
                        self.decoder.get_seed_indices(),
                        network=self.seed.network,
                        passphrase=self.passphrase
                    )
                if self.seed.type == SeedType.MONERO and seed.isLegacy:
                    seed2: Seed = LegacySeed.decodeIndices(
                        self.decoder.get_seed_indices(),
                        network=self.seed.network
                    )
                # Found a valid mnemonic seed! But does it match?
                if seed2.address != self.seed.address:
                    DireWarningScreen(
                        title='Confirm SeedQR',
                        status_headline='Error!',
                        text='Your transcribed SeedQR does not match your original seed!',
                        show_back_button=False,
                        button_data=['Review SeedQR'],
                    ).display()
                    return Destination(BackStackView, skip_current_view=True)
                LargeIconStatusScreen(
                    title='Confirm SeedQR',
                    status_headline='Success!',
                    text='Your transcribed SeedQR successfully scanned and yielded the same seed.',
                    show_back_button=False,
                    button_data=['OK'],
                ).display()
                return Destination(
                    SeedOptionsView,
                    view_args={
                        'seed': self.seed
                    }
                )
            # Will this case ever happen? Will trigger if a different
            # kind of QR code is scanned
            DireWarningScreen(
                title="Confirm SeedQR",
                status_headline="Error!",
                text="Your transcribed SeedQR could not be read!",
                show_back_button=False,
                button_data=["Review SeedQR"],
            ).display()
            return Destination(BackStackView, skip_current_view=True)
