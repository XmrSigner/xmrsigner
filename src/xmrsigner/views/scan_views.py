from ots.enums import SeedType
from ots.address import Address

from xmrsigner.controller import Controller, Flow
from xmrsigner.models.pending_seed import (
    PendingSeed,
    PendingSeedPhrase,
    PendingSeedIndices
)
from xmrsigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen
)
from xmrsigner.gui.button_data import ButtonData
from xmrsigner.models.qr_type import QrType
from xmrsigner.models.decode_qr import DecodeQR
from xmrsigner.models.settings import Setting, Option
from xmrsigner.views.settings_views import SettingsIngestSettingsQRView
from xmrsigner.views.view import (
    BackStackView,
    ErrorView,
    MainMenuView,
    NotYetImplementedView,
    OptionDisabledView,
    View,
    Destination
)
from xmrsigner.gui.constants import Icon as IconConstants
from xmrsigner.gui.theme import Theme


class ScanView(View):
    """
    The catch-all generic scanning View that will accept any of our supported QR
    formats and will route to the most sensible next step.

    Can also be used as a base class for more specific scanning flows with
    dedicated errors when an unexpected QR type is scanned (e.g. Scan Tx was
    selected but a SeedQR was scanned).
    """

    instructions_text = "Scan a QR code"
    invalid_qr_type_message = "QRCode not recognized or not yet supported."


    def __init__(self):
        super().__init__()
        # Define the decoder here to make it available to child classes' is_valid_qr_type
        # checks and so we can inject data into it in the test suite's `before_run()`.
        self.decoder: DecodeQR = DecodeQR()


    @property
    def is_valid_qr_type(self):
        return True

    def run(self):
        from xmrsigner.gui.screens.scan_screens import ScanScreen
        # Start the live preview and background QR reading
        self.run_screen(
            ScanScreen,
            instructions_text=self.instructions_text,
            decoder=self.decoder
        )
        # Handle the results
        if self.decoder.is_complete:
            if not self.is_valid_qr_type:
                # We recognized the QR type but it was not the type expected for the
                # current flow.
                # Report QR types in more human-readable text (e.g. QrType
                # `seed__compactseedqr` as "seed: compactseedqr").
                return Destination(
                    ErrorView,
                    view_args={
                        'title': 'Error',
                        'status_headline': 'Wrong QR Type',
                        'text': self.invalid_qr_type_message + f''', received "{self.decoder.qr_type.name.replace("_", " ")}" format''',
                        'button_text': 'Back',
                        'next_destination': Destination(BackStackView, skip_current_view=True),
                    }
                )
            if self.decoder.is_view_only_wallet:
                return Destination(ScanViewOnlyWalletView, view_args={'address': self.decoder.get_address()})
            if self.decoder.is_mnemonic or (self.decoder.is_wallet and not self.decoder.is_view_only_wallet):
                seed_mnemonic: list|None = self.decoder.get_seed_phrase()
                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    raise Exception('Invalid seed indices!')
                # Found a valid mnemonic seed! All new seeds should be considered
                #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                from xmrsigner.views.seed_views import SeedNetworkView
                # from xmrsigner.views.seed_views import SeedFinalizeView
                self.controller.pending_seed = PendingSeedPhrase(
                    mnemonic=seed_mnemonic,
                    type = SeedType.MONERO if len(seed_mnemonic) != 16 else SeedType.POLYSEED,
                    isLegacy = len(seed_mnemonic) in (12, 13),
                    height=self.decoder.decoder.height if self.decoder.is_wallet and isinstance(self.decoder.decoder.height, int) else None,
                    pre_filled = True
                )
                return Destination(SeedNetworkView, clear_history=True)
            if self.decoder.is_seed:
                seed_indices: SeedIndices|None = self.decoder.get_seed_indices()
                print(f'seed indices: {seed_indices.values}')
                if not seed_indices:
                    # seed is not valid, Exit if not valid with message
                    raise Exception('Invalid seed indices!')
                # Found a valid mnemonic seed! All new seeds should be considered
                #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                from xmrsigner.views.seed_views import SeedNetworkView
                # from xmrsigner.views.seed_views import SeedFinalizeView
                self.controller.pending_seed = PendingSeedIndices(
                    indices = seed_indices,
                    type = SeedType.MONERO if len(seed_indices) != 16 else SeedType.POLYSEED,
                    isLegacy = len(seed_indices) == 12,
                    pre_filled = True
                )
                print(f'pending seed: {self.controller.pending_seed}')
                return Destination(SeedNetworkView, clear_history=True)
            if self.decoder.is_address:
                from xmrsigner.views.monero_views import MoneroAddressSearchView
                return Destination(
                    MoneroAddressSearchView,
                    view_args={
                        'address': self.decoder.get_address(),
                        'seed': self.controller.selected_seed
                    },
                    clear_history=True
                )
            if self.decoder.is_ur:
                if self.decoder.qr_type == QrType.XMR_OUTPUT_UR:
                    self.controller.outputs: bytes = self.decoder.get_output()
                    if self.controller.selected_seed is not None:
                        from xmrsigner.views.monero_views import ImportOutputsView
                        return Destination(
                            ImportOutputsView,
                            view_args={
                                'seed': self.controller.selected_seed
                            },
                            skip_current_view=True
                        )
                    from xmrsigner.views.monero_views import MoneroSelectSeedView
                    return Destination(
                        MoneroSelectSeedView,
                        view_args={
                            'flow': Flow.SYNC
                        },
                        skip_current_view=True
                    )
                if self.decoder.qr_type == QrType.XMR_TX_UNSIGNED_UR:
                    tx: bytes = self.decoder.get_tx()
                    self.controller.transaction = tx
                    if self.controller.selected_seed is not None:
                        from xmrsigner.views.monero_views import MoneroSelectSeedView
                        return Destination(
                            OverviewView,
                            view_args={
                                'seed': self.controller.selected_seed
                            },
                            skip_current_view=True
                        )
                    from xmrsigner.views.monero_views import MoneroSelectSeedView
                    return Destination(
                        MoneroSelectSeedView,
                        view_args={
                            'flow': Flow.TX
                        },
                        skip_current_view=True
                    )
                raise Exception('Not Implemented Yet!')
            if self.decoder.is_settings:
                data = self.decoder.get_settings_data()
                return Destination(
                    SettingsIngestSettingsQRView,
                    view_args={
                        'data': data
                    }
                )
            if self.decoder.is_timestamp or self.decoder.is_date:
                button_data = ['Yes', 'No']
                qr_date: date = self.decoder.get_date()
                selected_menu_num = self.run_screen(
                    ButtonListScreen,
                    title=f'Set current date to {qr_date.isoformat()}',
                    is_button_text_centered=True,
                    button_data=button_data
                )
                if selected_menu_num == RET_CODE__BACK_BUTTON:
                    return Destination(ScanView, clear_history=True)
                if selected_menu_num == 0:
                    self.controller.date = qr_date
                    return Destination(
                        ScanDateTimeView,
                        clear_history=True,
                        view_args={
                            'is_date': self.decoder.is_date
                        }
                    )
                return Destination(MainMenuView, clear_history=True)
            return Destination(NotYetImplementedView)
        if self.decoder.is_invalid:
            # For now, don't even try to re-do the attempted operation, just reset and
            # start everything over.
            self.controller.resume_main_flow = None
            return Destination(ErrorView, view_args={
                'title': 'Error',
                'status_headline': 'Unknown QR Type',
                'text': 'QRCode is invalid or is a data format not yet supported.',
                'button_text': 'Done',
                'next_destination': Destination(MainMenuView, clear_history=True)
            })
        return Destination(MainMenuView)


class ScanUR2View(ScanView):

    instructions_text = "Scan UR"
    invalid_qr_type_message = "Expected a UR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_ur


class ScanOutputsView(ScanUR2View):  # TODO: 2024-07-23, implement in SeedOptions

    instructions_text = "Scan Outputs UR"
    invalid_qr_type_message = "Expected a UR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_outputs


class ScanUnsignedTransactionView(ScanUR2View):  # TODO: 2024-07-23, implement in SeedOptions

    instructions_text = "Scan Unsigned TX UR"
    invalid_qr_type_message = "Expected a UR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_tx_unsigned


class ScanSeedQRView(ScanView):

    instructions_text = "Scan SeedQR"
    invalid_qr_type_message = f"Expected a SeedQR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_seed or self.decoder.is_mnemonic


class ScanAddressView(ScanView):

    instructions_text = "Scan address QR"
    invalid_qr_type_message = "Expected an address QR"

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_address


class ScanViewOnlyWalletView(View):

    def __init__(
        self,
        address: Address
    ):
        super().__init__()
        self.address: Address = address

    def run(self):
        from xmrsigner.gui.screens.scan_screens import ScanViewOnlyWalletScreen
        self.run_screen(ScanViewOnlyWalletScreen, address=self.address)
        return Destination(MainMenuView)


class ScanDateTimeView(View):

    def __init__(
        self,
        is_date: bool = True
    ):
        super().__init__()
        self.is_date: bool = is_date

    def run(self):
        text: str = f'''
Set current {'date' if self.is_date else 'timestamp'} to {self.controller.date if self.is_date else self.controller.timestamp} ({self.controller.timestamp if self.is_date else self.controller.date}).
'''
        from xmrsigner.gui.screens.screen import LargeIconStatusScreen
        self.run_screen(
            LargeIconStatusScreen,
            title = 'Set Date',
            show_back_button = False,
            status_icon_name = IconConstants.SUCCESS,
            status_icon_size = Theme.ICON_PRIMARY_SCREEN_SIZE,
            status_color = Theme.SUCCESS_COLOR,
            status_headline = 'Success!',
            text = text,
            button_data = [ ButtonData('OK') ]
        )
        return Destination(MainMenuView)
