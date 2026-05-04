from json import load, dump, dumps
from os import path, remove, fsync
from platform import uname

from xmrsigner.models.settings_definition import (
    Setting,
    Type,
    Option,
    Network,
    CameraRotation,
    Visibility,
    SettingsConstants,
    SettingsDefinition,
    SelectionOption,
    MicroSdAction
)
from xmrsigner.models.singleton import Singleton


class InvalidSettingsQRData(Exception):
    pass


class Settings(Singleton):
    HOSTNAME = uname()[1]  # TODO: 2024-06-30 don't know what will uname return on win32, check
    XMRSIGNER_OS = 'xmrsigner-os'
    SETTINGS_FILENAME = '/mnt/microsd/settings.json' if HOSTNAME == XMRSIGNER_OS else 'settings.json'
    MICROSD_MOUNT_POINT = '/mnt/microsd'
    MICROSD_FIFO_PATH = '/tmp/mdev_fifo'
    MICROSD_FIFO_MODE = 0o600

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance._data = SettingsDefinition.get_defaults()
            # Read persistent settings file, if it exists
            if path.exists(Settings.SETTINGS_FILENAME):
                with open(Settings.SETTINGS_FILENAME) as settings_file:
                    cls._instance.load(load(settings_file))
        return cls._instance

    @classmethod
    def parse_settingsqr(cls, data: str) -> tuple[str, dict[Setting, any]]:
        """
        Parses SettingsQR data and returns a tuple of (config_name, settings_dict).
        The resulting settings config can be applied by calling `Settings.update(settings_dict)`.
        """
        if not data.startswith('settings::'):
            raise InvalidSettingsQRData()
        header, data = data.split(maxsplit=1)
        version = header.split('::')[1]
        if version != 'v1':
            raise InvalidSettingsQRData(f'Unsupported SettingsQR version: {version}')
        # handle optional 'name' attr
        config = {k: v for k, v in [e.split('=') for e in [e for e in data.split()]]}
        config_name = None
        if 'name' in config:
            config_name = config['name'].replace('_', ' ')
            del config['name']
        updated_settings = {}
        for abbreviated_name, value in config.items:
            # Replace abbreviated name with full attr
            settings_entry = SettingsDefinition.get_settings_entry_by_abbreviated_name(abbreviated_name)
            if not settings_entry:
                print(f'Ignoring unrecognized attribute: {abbreviated_name}')
                continue
            # Parse multi-value settings; integer-ize where needed
            values = [
                int(v) if v.isdigit() else v
                for v in (value.split(',') if settings_entry.type == Type.MULTISELECT else [value])
            ]
            options = {opt.config_value: opt for opt in settings_entry.selection_options}
            if settings_entry.attr == Setting.PERSISTENT_SETTINGS:
                # Special case: if trying to enable Persistent Settings when
                # DISABLED is the only option allowed (because the SD card is not
                # inserted. Explicitly set to DISABLED.
                updated_settings[settings_entry.attr] = Option.DISABLED if (values[0] == Option.ENABLED.value and values[0] not in options) else options[values[0]]
                continue
            # Validate value(s) against SettingsDefinition's valid options
            for v in values:
                if v not in options:
                    raise InvalidSettingsQRData(f"""{abbreviated_name} = '{v}' is not valid""")
            updated_settings[settings_entry.attr] = [options[v] for v in values] if settings_entry.type == Type.MULTISELECT else options[values[0]]
        return (config_name, updated_settings)

    def __str__(self):
        return dumps(self._data, indent=4)

    def save(self):
        if self._data[Setting.PERSISTENT_SETTINGS] == Option.ENABLED:
            with open(Settings.SETTINGS_FILENAME, 'w') as settings_file:
                dump(
                    {
                        k.value: v.value if not isinstance(v, list) else ','.join([e.value for e in v])
                        for k, v in self._data.items()
                    },
                    settings_file,
                    indent=4
                )
                # XmrSignerOS makes removing the microsd possible, flush and then fsync forces persistent settings to disk
                # without this, recent settings changes could be missing after the microsd card was removed
                settings_file.flush()
                fsync(settings_file.fileno())

    def load(self, json: dict) -> None:
        settings = {e.value: e for e in Setting}
        new_settings = {}
        for k, v in json:
            key = settings[k]
            settings_entry = SettingsDefinition.get_settings_entry(key)
            options = {e.config_value: e for e in settings_entry.selection_options}
            value = options[int(v) if v.isdigit() else v] if settings_entry.type != Type.MULTISELECT else [options[int(e) if e.isdigit() else e] for e in v]
            new_settings[key] = value
        self.update(new_settings)

    def update(self, new_settings: dict[Setting, any]):
        """
        Replaces the current settings with the incoming dict.
        """
        self._data.update(new_settings)

    def set_value(self, attr: Setting, value: SelectionOption|list[SelectionOption]|str|int):
        """
        Updates the attr's current value.
        Note that for multiselect, the value must be a List.
        """
        if attr not in self._data:
            raise Exception(f'Setting for {attr.name} not found')
        if SettingsDefinition.get_settings_entry(attr).type == Type.MULTISELECT:
            if type(value) != list:
                raise Exception(f'value must be a List for {attr.name}')
        # Special handling for toggling persistence
        if attr == Setting.PERSISTENT_SETTINGS and value == Option.DISABLED:
            try:
                remove(self.SETTINGS_FILENAME)
                print(f'Removed {self.SETTINGS_FILENAME}')
            except:
                print(f'{self.SETTINGS_FILENAME} not found to be removed')
        self._data[attr] = value
        self.save()

    def get_value(self, attr: Setting) -> SelectionOption|list[SelectionOption]|str|int:
        """
        Returns the attr's current value.
        Note that for multiselect, the current value is a List.
        """
        if attr not in self._data:
            raise Exception(f'Setting for {attr.name} not found')
        return self._data[attr]

    def get_value_display_name(self, attr: Setting) -> str:
        """
        Figures out the mapping from value to display_name for the current value's
        tuple(value, display_name) definition, if it's defined that way.

        Cannot be used for multiselect (use get_multiselect_value_display_names
        instead) or free entry types (there is no tuple mapping).
        """
        if attr not in self._data:
            raise Exception(f'Setting for {attr.name} not found')
        settings_entry = SettingsDefinition.get_settings_entry(attr)
        if settings_entry.type == Type.MULTISELECT:
            raise Exception(f'Unsupported SettingsEntry.type: {settings_entry.type.name}')
        return self._data[attr].display

    def get_multiselect_value_display_names(self, attr: Setting) -> list[str]:
        """
        Returns a List of all the selected values' display_names.
        """
        if attr not in self._data:
            raise Exception(f'Setting for {attr.name} not found')
        settings_entry = SettingsDefinition.get_settings_entry(attr)
        if settings_entry.type != Type.MULTISELECT:
            raise Exception(f'Unsupported SettingsEntry.type: {settings_entry.type.name}')
        # Iterate through the selection_options list in order to preserve intended sort
        # order when adding which options are selected.
        return [e.display for e in settings_entry.selection_options if e in self._data[attr]]

    """
    Intentionally keeping the properties very limited to avoid an expectation of
    boilerplate property code for every SettingsEntry.

    It's more cumbersome, but instead use:
        settings.get_value(Setting.MY_SETTING_ATTR)
    """
    @property
    def debug(self) -> bool:
        return self._data[Setting.DEBUG] == Option.ENABLED

    def handle_microsd_state_change(action: MicroSdAction):
        """
        Enables/Disables the Persistent Settings option based on the MicroSD card state.
        """
        if Settings.HOSTNAME == Settings.XMRSIGNER_OS:
            if action == MicroSdAction.INSERTED:
                # SD card was just inserted.
                # Restore persistent settings back to defaults
                entry = SettingsDefinition.get_settings_entry(Setting.PERSISTENT_SETTINGS)
                entry.selection_options = Option.enabled_disabled()
                entry.help_text = SettingsConstants.PERSISTENT_SETTINGS__SD_INSERTED__HELP_TEXT
                # - Overwrite settings on the SD?
                # - Load settings from SD?
                # if Settings file exists (meaning persistent settings was previously enabled), write out current settings to disk
                if path.exists(Settings.SETTINGS_FILENAME):
                    # enable persistent settings first, then save
                    Settings.get_instance()._data[Setting.PERSISTENT_SETTINGS] = Option.ENABLED
                    Settings.get_instance().save()
                return
            if action == MicroSdAction.REMOVED:
                # SD card was just removed.
                # Set persistent settings to disabled value directly
                Settings.get_instance()._data[Setting.PERSISTENT_SETTINGS] = Option.DISABLED
                # set persistent settings to only have disabled as an option, adding additional help text that microSD is removed
                entry = SettingsDefinition.get_settings_entry(Setting.PERSISTENT_SETTINGS)
                entry.selection_options = [Option.DISABLED]
                entry.help_text = SettingsConstants.PERSISTENT_SETTINGS__SD_REMOVED__HELP_TEXT
                return
