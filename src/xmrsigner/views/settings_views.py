from logging import getLogger

from xmrsigner.gui.button_data import ButtonData
from xmrsigner.gui.components import (
    FontAwesome,
    IconConstants
)
from xmrsigner.models.decode_qr import DecodeQR
from xmrsigner.views.view import (
    View,
    Destination,
    MainMenuView
)
from xmrsigner.gui.screens import (
    RET_CODE__BACK_BUTTON,
    ButtonListScreen,
    settings_screens
)
from xmrsigner.models.settings import (
    SettingsDefinition,
    Setting,
    Visibility
)
from xmrsigner.models.settings_definition import Type
from xmrsigner.hardware.microsd import MicroSD


logger = getLogger(__name__)


class SettingsMenuView(View):

    IO_TEST = ButtonData('I/O test')
    DONATE = ButtonData('Donate')
    ABOUT = ButtonData('About')
    ADVANCED = ButtonData('Advanced', right_icon_name = IconConstants.CHEVRON_RIGHT)

    def __init__(
        self,
        visibility: Visibility = Visibility.GENERAL,
        selected_attr: Setting|None = None,
        initial_scroll: int = 0
    ):
        super().__init__()
        self.visibility: Visibility = visibility
        self.selected_attr: Setting = selected_attr
        # Used to preserve the rendering position in the list
        self.initial_scroll: int = initial_scroll

    def run(self):
        settings_entries = SettingsDefinition.get_settings_entries(
            visibility=self.visibility
        )
        button_data=[e.display_name for e in settings_entries]
        selected_button: int = 0
        if self.selected_attr:
            for i, entry in enumerate(settings_entries):
                if entry.attr == self.selected_attr:
                    selected_button = i
                    break
        if self.visibility == Visibility.GENERAL:
            title = 'Settings'
            # Set up the next nested level of menuing
            button_data.append(self.ADVANCED)
            button_data.append(self.DONATE)
            button_data.append(self.ABOUT)
        elif self.visibility == Visibility.ADVANCED:
            title = 'Advanced'
            button_data.append(self.IO_TEST)
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=title,
            is_button_text_centered=False,
            button_data=button_data,
            selected_button=selected_button,
            scroll_y_initial_offset=self.initial_scroll,
        )
        # Preserve our scroll position in this Screen so we can return
        initial_scroll = self.screen.buttons[0].scroll_y
        if selected_menu_num == RET_CODE__BACK_BUTTON:
            if self.visibility == Visibility.GENERAL:
                return Destination(MainMenuView)
            if self.visibility == Visibility.ADVANCED:
                return Destination(SettingsMenuView)
            return Destination(SettingsMenuView, view_args={'visibility': Visibility.ADVANCED})
        if len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.IO_TEST:
            return Destination(IOTestView)
        if len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.ADVANCED:
            return Destination(SettingsMenuView, view_args={'visibility': Visibility.ADVANCED})
        if len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.DONATE:
            return Destination(DonateView)
        if len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.ABOUT:
            return Destination(AboutView)
        return Destination(SettingsEntryUpdateSelectionView, view_args={'attr': settings_entries[selected_menu_num].attr})


class SettingsEntryUpdateSelectionView(View):
    """
    Handles changes to all selection-type settings (Multiselect, SELECT_1,
    Enabled/Disabled, etc).
    """

    def __init__(
        self,
        attr: Setting,
        parent_initial_scroll: int = 0,
        selected_button: int = None
    ):
        super().__init__()
        self.settings_entry = SettingsDefinition.get_settings_entry(attr)
        self.selected_button = selected_button
        self.parent_initial_scroll = parent_initial_scroll

    def run(self):
        initial_value: SelectionOption = self.settings.get_value(self.settings_entry.attr)
        button_data = []
        checked_buttons = []
        selection_options: list[SelectionOption] = self.settings_entry.selection_options
        print(f'initial_value: {initial_value}({type(initial_value)}')
        print(f'selection_options: {selection_options}')
        for i, option in enumerate(selection_options):
            print(f'{option}: {type(option)}')
            button_data.append(option.display)
            print(f'{initial_value} == {option}? {initial_value==option}')
            if (type(initial_value) == list and option in initial_value) or option == initial_value:
                checked_buttons.append(i)
                if self.selected_button is None:
                    # Highlight the selection (for multiselect highlight the first
                    # selected option).
                    self.selected_button = i
        if self.selected_button is None:
            self.selected_button = 0
        ret_value = self.run_screen(
            settings_screens.SettingsEntryUpdateSelectionScreen,
            display_name=self.settings_entry.display_name,
            help_text=self.settings_entry.help_text,
            button_data=button_data,
            selected_button=self.selected_button,
            checked_buttons=checked_buttons,
            settings_entry_type=self.settings_entry.type
        )
        destination = None
        settings_menu_view_destination = Destination(
            SettingsMenuView,
            view_args={
                'visibility': self.settings_entry.visibility,
                'selected_attr': self.settings_entry.attr,
                'initial_scroll': self.parent_initial_scroll
            }
        )
        if ret_value == RET_CODE__BACK_BUTTON:
            return settings_menu_view_destination
        value = selection_options[ret_value]
        if self.settings_entry.type == Type.MULTISELECT:
            updated_value = list(initial_value)
            if ret_value not in checked_buttons:
                # This is a new selection to add
                updated_value.append(value)
            else:
                # This is a de-select to remove
                updated_value.remove(value)
        else:
            # All other types are single selects (e.g. Enabled/Disabled, SELECT_1)
            if value == initial_value:
                # No change, return to menu
                return settings_menu_view_destination
            else:
                updated_value = value
        self.settings.set_value(
            attr=self.settings_entry.attr,
            value=updated_value
        )
        if destination:
            return destination
        # All selects stay in place; re-initialize where in the list we left off
        self.selected_button = ret_value
        return Destination(
            SettingsEntryUpdateSelectionView,
            view_args={
                'attr': self.settings_entry.attr,
                'parent_initial_scroll': self.parent_initial_scroll,
                'selected_button': self.selected_button
            },
            skip_current_view=True
        )


class SettingsIngestSettingsQRView(View):

    def __init__(self, data: str):
        super().__init__()

        # May raise an Exception which will bubble up to the Controller to display to the
        # user.
        return Destination(
            SettingsEntryUpdateSelectionView,
            view_args={
                'attr': self.settings_entry.attr,
                'parent_initial_scroll': self.parent_initial_scroll,
                'selected_button': self.selected_button
            },
            skip_current_view=True
        )


class SettingsIngestSettingsQRView(View):

    def __init__(self, data: str):
        super().__init__()
        # May raise an Exception which will bubble up to the Controller to display to the
        # user.
        self.config_name, settings_update_dict = Settings.parse_settingsqr(data)
        self.settings.update(settings_update_dict)
        if MicroSD.get_instance().is_inserted and self.settings.get_value(Setting.PERSISTENT_SETTINGS) == Option.ENABLED:
            self.status_message = 'Persistent Settings enabled. Settings saved to SD card.'
        else:
            self.status_message = 'Settings updated in temporary memory'

    def run(self):
        from xmrsigner.gui.screens.settings_screens import SettingsQRConfirmationScreen
        self.run_screen(
            SettingsQRConfirmationScreen,
            config_name=self.config_name,
            status_message=self.status_message,
        )
        # Only one exit point
        return Destination(MainMenuView)


"""****************************************************************************
    Misc
****************************************************************************"""
class IOTestView(View):

    def run(self):
        self.run_screen(settings_screens.IOTestScreen)
        return Destination(SettingsMenuView)


class DonateView(View):

    def run(self):
        self.run_screen(settings_screens.DonateScreen)
        return Destination(SettingsMenuView)


class AboutView(View):

    def run(self):
        self.run_screen(settings_screens.AboutScreen)
        return Destination(SettingsMenuView)
