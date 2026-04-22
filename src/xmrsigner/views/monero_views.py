from ots.enums import SeedType
from ots.seed import Seed
from ots.seed_jar import SeedJar
from ots.transaction import (
    Transaction,
    TxDescription
)

from xmrsigner.controller import Controller, Flow
from xmrsigner.gui.button_data import (
    ButtonData,
    FingerprintButtonData
)
from xmrsigner.gui.components import (
    GUIConstants,
    FontAwesomeIconConstants,
    IconConstants
)
from xmrsigner.models.monero_encoder import MoneroSignedTxQrEncoder
from xmrsigner.models.settings_definition import Setting
from xmrsigner.gui.screens.monero_screens import (
    TxOverviewScreen,
    TxMathScreen,
    TxAddressDetailsScreen,
    TxChangeDetailsScreen,
    TxFinalizeScreen,
    DateOrBlockHeightScreen
)
from xmrsigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    DireWarningScreen,
    LoadingScreenThread,
    QRDisplayScreen,
    WarningScreen
)
from xmrsigner.views.wallet_views import ImportOutputsView
from xmrsigner.views.view import (
    BackStackView,
    MainMenuView,
    NotYetImplementedView,
    View,
    Destination
)


class MoneroSelectSeedView(View):

    SCAN_SEED = ButtonData('Scan a seed').with_icon(FontAwesomeIconConstants.QRCODE)
    TYPE_13WORD = ButtonData('Enter 13-word seed').with_icon(FontAwesomeIconConstants.KEYBOARD)
    TYPE_25WORD = ButtonData('Enter 25-word seed').with_icon(FontAwesomeIconConstants.KEYBOARD)

    def __init__(self, flow: Flow):
        super().__init__()
        self.flow: Flow = flow

    def run(self):
        button_data = []
        for seed in SeedJar.seeds():
            button_data.append(
                FingerprintButtonData(
                    seed.fingerprint,
                    False,
                    seed.type == SeedType.POLYSEED,
                    seed.isLegacy
                )
            )
        button_data.append(self.SCAN_SEED)
        button_data.append(self.TYPE_13WORD)
        button_data.append(self.TYPE_25WORD)
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title='Select Seed',
            is_button_text_centered=False,
            button_data=button_data
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if SeedJar.count() > 0 and selected_menu_num < SeedJar.count():
            # User selected one of the n seeds
            self.controller.selected_seed = SeedJar.forIndex(selected_menu_num)
            if self.flow == Flow.SYNC:
                return Destination(
                    ImportOutputsView,
                    view_args={
                        'seed': self.controller.selected_seed
                    }
                )
            if self.flow == Flow.TX:
                return Destination(
                    OverviewView,
                    view_args={
                        'seed': self.controller.selected_seed
                    }
                )
        # The remaining flows are a sub-flow; resume PSBT flow once the seed is loaded.
        # self.controller.resume_main_flow = Flow.TX
        self.controller.resume_main_flow = self.flow
        if button_data[selected_menu_num] == self.SCAN_SEED:
            from xmrsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)
        if button_data[selected_menu_num] in [self.TYPE_13WORD, self.TYPE_25WORD]:
            from xmrsigner.views.seed_views import SeedMnemonicEntryView
            if button_data[selected_menu_num] == self.TYPE_13WORD:
                self.controller.pending_seed = PendingSeed(isLegacy=True)
            else:
                self.controller.pending_seed = PendingSeed()
            return Destination(SeedMnemonicEntryView)


class OverviewView(View):

    def __init__(self, seed: Seed|None = None):
        super().__init__()
        self.seed: Seed = seed

        self.loading_screen = None

        if not self.controller.tx_description:
            # Parsing could take a while. Run the loading screen while we wait.
            from xmrsigner.gui.screens.screen import LoadingScreenThread
            self.loading_screen = LoadingScreenThread(text="Parsing Transaction...")
            self.loading_screen.start()

    def run(self):
        try:
            txd: TxDescription|None = self.seed.wallet.describeTransfer(self.controller.transaction)
            # Everything is set. Stop the loading screen
            if self.loading_screen:
                self.loading_screen.stop()
        except Exception as e:
            self.loading_screen.stop()
            raise e
        self.loading_screen.stop()
        if txd is None:
            selected_menu_num = WarningScreen(
                status_headline='No valid Transaction',
                text="This Transaction seems to be invalid.",
                button_data=[ButtonData.CONTINUE],
            ).display()
            return Destination(MainMenuView)
        self.controller.tx_description = txd
        # Run the overview screen
        selected_menu_num = self.run_screen(
            TxOverviewScreen,
            spend_amount=int(txd.amount_out),
            change_amount=int(txd.change_amount),
            fee_amount=int(txd.fee),
            num_inputs=txd.inputs,
            num_self_transfer_outputs=txd.outputs,
            num_change_outputs=txd.change_outputs,
            destination_addresses=[str(r.address) for r in txd.recipients]
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            self.controller.transaction = None
            self.controller.selected_seed = None
            return Destination(BackStackView)
        if txd.change_amount == 0:
            return Destination(NoChangeWarningView)
        return Destination(MathView)


class NoChangeWarningView(View):
    def run(self):
        selected_menu_num = WarningScreen(
            status_headline="Full Spend!",
            text="This Transaction spends its entire input value. No change is coming back to your wallet.",
            button_data=[ButtonData.CONTINUE],
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(
            MathView,
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )


class MathView(View):
    """
    Follows the Overview pictogram. Shows:
    + total input value
    - recipients' value
    - fees
    -------------------
    + change value
    """
    def run(self):
        if not self.controller.transaction:
            # Should not be able to get here
            return Destination(MainMenuView)
        txd: TxDescription = self.controller.tx_description
        selected_menu_num = self.run_screen(
            TxMathScreen,
            input_amount=int(txd.amount_in),
            num_inputs=txd.inputs,
            spend_amount=int(txd.amount_out),
            num_recipients=len(txd.recipients),
            fee_amount=int(txd.fee),
            change_amount=int(txd.change_amount),
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if len(txd.recipients) > 0:
            return Destination(TxAddressDetailsView, view_args={'address_num': 0})
        # This is a self-transfer
        return Destination(TxChangeDetailsView, view_args={'change_address_num': 0})


class TxAddressDetailsView(View):
    '''
    Shows the recipient's address and amount they will receive
    '''
    def __init__(self, address_num: int):
        super().__init__()
        self.address_num: int = address_num

    def run(self):
        if self.controller.tx_description is None:
            # Should not be able to get here
            raise Exception('Routing error')
        txd: TxDescription = self.controller.tx_description
        title = 'Will Send'
        if len(txd.recipients) > 1:
            title += f' (#{self.address_num + 1})'

        if self.address_num < len(txd.recipients) - 1:
            button_data = [ButtonData('Next Recipient')]
        else:
            button_data = [ButtonData.NEXT]
        print(txd.recipients)
        print(f'self.address_num: {self.address_num}')
        print(txd.recipients[self.address_num])
        selected_menu_num = self.run_screen(
            TxAddressDetailsScreen,
            title=title,
            button_data=button_data,
            address=str(txd.recipients[self.address_num].address),
            amount=str(txd.recipients[self.address_num].amount),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if self.address_num < len(txd.recipients) - 1:
            # Show the next receive addr
            return Destination(TxAddressDetailsView, view_args={'address_num': self.address_num + 1})
        if txd.change_amount > 0 and False:  # TODO: 2024-07-27, decide what to do about
            # Move on to display change
            return Destination(TxChangeDetailsView, view_args={'change_address_num': 0})
        # There's no change output to verify. Move on to sign the Tx.
        return Destination(FinalizeView)


class TxChangeDetailsView(View):

    NEXT = ButtonData.NEXT

    def __init__(self, change_address_num):
        super().__init__()
        self.change_address_num = change_address_num
        loading_screen: Optional[LoadingScreenThread] = None

    def run(self):
        if not self.controller.tx_description:
            # Should not be able to get here
            return Destination(MainMenuView)
        txd: TxDescription = self.controller.tx_description
        title = 'Self-Transfer'
        try:
            if is_change_derivation_path:
                loading_screen_text = 'Verifying Change...'
            else:
                loading_screen_text = 'Verifying Self-Transfer...'
            self.loading_screen = LoadingScreenThread(text=loading_screen_text)
            self.loading_screen.start()
            network = txd.network
            if txd.change_addresses[self.change_address_num] == calc_address or True:  # TODO: 2024-07-27, decide to check or remove
                is_change_addr_verified = True
                button_data = [self.NEXT]
        finally:
            if self.loading_screen:
                self.loading_screen.stop()
        if is_change_addr_verified == False:
            return Destination(AddressVerificationFailedView, view_args=dict(is_change=is_change_derivation_path), clear_history=True)
        selected_menu_num = self.run_screen(
            TxChangeDetailsScreen,
            title=title,
            button_data=button_data,
            address=change_data.get('address'),
            amount=change_data.get('amount'),
            is_multisig=False,
            fingerprint=seed_fingerprint,
            derivation_path=None,
            is_change_derivation_path=is_change_derivation_path,
            derivation_path_addr_index=derivation_path_addr_index,
            is_change_addr_verified=is_change_addr_verified,
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == self.NEXT:
            if self.change_address_num < tx_parser.num_change_outputs - 1:
                return Destination(TxChangeDetailsView, view_args={'change_address_num': self.change_address_num + 1})
            # There's no more change to verify. Move on to sign the Tx.
            return Destination(FinalizeView)


class AddressVerificationFailedView(View):

    def __init__(self, is_change: bool = True, is_multisig: bool = False):
        super().__init__()
        self.is_change = is_change

    def run(self):
        self.run_screen(
            DireWarningScreen,
            title='Suspicious Transaction',
            status_headline='Address Verification Failed',
            text=f'Transactions {"change" if self.is_change else "self-transfer"} address could not be generated from your seed.',
            button_data=[ButtonData('Discard Transaction')],
            show_back_button=False,
        )
        # We're done with this Tx. Route back to MainMenuView which always
        #   clears all ephemeral data (except in-memory seeds).
        return Destination(MainMenuView, clear_history=True)


class FinalizeView(View):

    APPROVE_TX = ButtonData('Approve Transaction')

    def run(self):
        if not self.controller.tx_description:
            # Should not be able to get here
            return Destination(MainMenuView)
        tx_description: TxDescription = self.controller.tx_description
        transaction: Transaction = self.controller.transaction
        selected_menu_num = self.run_screen(
            TxFinalizeScreen,
            button_data=[self.APPROVE_TX]
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        return Destination(SignedQRDisplayView)


class SignedQRDisplayView(View):

    def __init__(self):
        super().__init__()
        self.seed: Seed = self.controller.selected_seed
        self.wallet: MoneroWallet = self.controller.get_wallet(self.seed.network)
        self.loading_screen = None
        if not self.controller.transaction:
            return Destination(MainMenuView)
        # Parsing could take a while. Run the loading screen while we wait.
        from xmrsigner.gui.screens.screen import LoadingScreenThread
        self.loading_screen = LoadingScreenThread(text=f'Sign Tx for seed {self.seed.fingerprint}...')
        self.loading_screen.start()

    def run(self):
        try:
            signed_tx: bytes = self.seed.wallet.signTransaction(self.controller.transaction)
            if not signed_tx:
                raise Exception('No valid transaction')
            qr_encoder = MoneroSignedTxQrEncoder(
                signed_tx,
                self.settings.get_value(Setting.QR_DENSITY)
            )
        except Exception as e:
            if self.loading_screen:
                self.loading_screen.stop()
            return Destination(SigningErrorView)
        if self.loading_screen:
            self.loading_screen.stop()
        self.run_screen(QRDisplayScreen, qr_encoder=qr_encoder)
        # We're done with this Tx. Route back to MainMenuView which always
        #   clears all ephemeral data (except in-memory seeds).
        return Destination(MainMenuView, clear_history=True)


class SigningErrorView(View):

    SELECT_DIFF_SEED = ButtonData('Select Diff Seed')

    def run(self):
        if not self.controller.tx_description:
            # Should not be able to get here
            return Destination(MainMenuView)
        txd: TxDescription = self.controller.tx_description
        # Just a WarningScreen here; only use DireWarningScreen for true security risks.
        selected_menu_num = self.run_screen(
            WarningScreen,
            title='Transaction Error',
            status_icon_name=IconConstants.WARNING,
            status_headline='Signing Failed',
            text='Signing with this seed did not add a valid signature.',
            button_data=[self.SELECT_DIFF_SEED],
        )
        # TODO: 2024-07-27, code missing here!
        if selected_menu_num == 0:
            # clear seed selected for psbt signing since it did not add a valid signature
            self.controller.selected_seed = None
            return Destination(SelectSeedView, clear_history=True)
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

class DateOrBlockHeightView(View):

    def run(self):
        result: Union[str, int] = self.run_screen(
            DateOrBlockHeightScreen
        )
        if result == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        self.controller.block_height = int(result)
