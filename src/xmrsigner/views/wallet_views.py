from ots.seed_jar import SeedJar
from ots.seed import Seed

from xmrsigner.models.monero_encoder import MoneroKeyImageQrEncoder
from xmrsigner.views.view import (
    NotYetImplementedView,
    View,
    Destination,
    BackStackView,
    MainMenuView
)
from xmrsigner.models.monero_encoder import (
    ViewOnlyWalletQrEncoder,
    ViewOnlyWalletJsonQrEncoder
)
from xmrsigner.gui.screens import (
    seed_screens,
	WarningScreen,
	ButtonListScreen,
	LargeIconStatusScreen
)
from xmrsigner.models.settings_definition import (
    SettingsDefinition,
	ViewOnlyWalletFormat,
	Setting
)
from xmrsigner.gui.button_data import ButtonData
from xmrsigner.gui.components import (
    IconConstants,
	FontAwesomeIconConstants,
	GUIConstants
)
from xmrsigner.gui.screens.wallet_screens import WalletOptionsScreen
from xmrsigner.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
	QRDisplayScreen
)


class WalletViewKeyQRView(View):

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        wallet_qr_format: ViewOnlyWalletFormat|None = None
        if len(self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)) > 1:
            ret = self.run_screen(
                    ButtonListScreen,
                    title=SettingsDefinition.get_settings_entry(Setting.VIEW_WALLET_QR_FORMAT).display_name,
                    button_data=[ButtonData(format) for format in self.settings.get_multiselect_value_display_names(Setting.VIEW_WALLET_QR_FORMAT)]
            )
            wallet_qr_format = self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)[ret]
        else:
            wallet_qr_format = self.settings.get_value(Setting.VIEW_WALLET_QR_FORMAT)[0]
        if wallet_qr_format == ViewOnlyWalletFormat.URI:
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


class WalletViewKeyJsonQRView(WalletViewKeyQRView):

    def run(self):
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=ViewOnlyWalletJsonQrEncoder(self.seed.wallet, self.seed.height)
        )
        return Destination(BackStackView)


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
        self.run_screen(LargeIconStatusScreen, title='Load Outputs', text=f"Wallet {self.seed.fingerprint} has not received funds yet.", status_headline='No balance found!')
        return Destination(MainMenuView)  # TODO: 2024-07-27, thought: redirect to address viewer as soon it exists


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
            num_imported = self.seed.wallet.importOutputs(self.controller.outputs)
            if int(num_imported) == 0:  # we have a zero balance
                if self.loading_screen:
                    self.loading_screen.stop()
                return Destination(NoOutputsImportedView, view_args={'seed': self.seed})
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


# TODO: move to SeedOptionsView
class WalletOptionsView(View):
    """
    Views for actions on individual seeds:
    """

    SCAN = ButtonData('Scan for Wallet').with_icon(IconConstants.SCAN)
    EXPORT_KEY_IMAGES = ButtonData('Export Key Imags').with_icon(IconConstants.QRCODE)
    VIEW_ONLY_WALLET = ButtonData('View only Wallet').with_icon(IconConstants.QRCODE)

    def __init__(self, seed: Seed):
        super().__init__()
        self.seed: Seed = seed

    def run(self):
        button_data = []
        button_data.append(self.SCAN)
        button_data.append(self.EXPORT_KEY_IMAGES)
        button_data.append(self.VIEW_ONLY_WALLET)
        selected_menu_num = self.run_screen(
            WalletOptionsScreen,
            button_data=button_data,
            fingerprint=self.seed.fingerprint,
            polyseed=self.seed.type == SeedType.POLYSEED,
            my_monero=self.seed.isLegacy
        )
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if button_data[selected_menu_num] == self.SCAN:
            from xmrsigner.views.scan_views import ScanUR2View
            return Destination(ScanUR2View)
        if button_data[selected_menu_num] == self.VIEW_ONLY_WALLET:
            return Destination(WalletViewKeyQRView, view_args={'seed': self.seed})
        if button_data[selected_menu_num] == self.EXPORT_KEY_IMAGES:
            return Destination(ExportKeyImagesView, view_args={'seed': self.seed})
