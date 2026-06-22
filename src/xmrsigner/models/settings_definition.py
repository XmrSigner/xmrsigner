from enum import Enum
from dataclasses import dataclass

from ots.seed_language import SeedLanguage
from ots.enums import SeedType
from ots.enums import Network as OtsNetwork


class MicroSdAction(Enum):

    INSERTED = 'add'
    REMOVED = 'remove'


class SelectionOption:

    name: str
    value: str|int

    @property
    def display(self) -> str:
        return self.name.replace('_', ' ').title()

    @property
    def config_value(self) -> str|int:
        return self.value.value

    def __str__(self) -> str:
        return self.value if type(self.value) == str else str(int)


class Choice(SelectionOption, Enum):

    @classmethod
    def all(cls) -> list:
        return [c for c in cls]


class BackupTestMethod(Choice):

    COMPLETE = 25
    PARTIAL = 4
    ONE_WORD = 1


class Network(Choice):

    MAIN = OtsNetwork.MAIN
    TEST = OtsNetwork.TEST
    STAGE = OtsNetwork.STAGE

    @property
    def config_value(self) -> str|int:
        return self.name[0]

    def __str__(self) -> str:
        return self.value.name


class Option(Choice):

    ENABLED = 'E'
    DISABLED = 'D'
    PROMPT = 'P'
    REQUIRED = 'R'

    @classmethod
    def enabled_disabled(cls) -> list:
        return [cls.ENABLED, cls.DISABLED]

    @classmethod
    def required(cls) -> list:
        return [cls.ENABLED, cls.DISABLED, cls.REQUIRED]

    @classmethod
    def prompt(cls) -> list:
        return [cls.ENABLED, cls.DISABLED, cls.PROMPT]


class QrDisplayBrightness(Choice):
    MIN = 31
    VERY_DARK = 40
    DARK = 50
    MEDIUM = 60
    DEFAULT = 62
    BRIGHT = 80
    VERY_BRIGHT = 150
    MAX = 255

    @classmethod
    def _missing_(cls, value: int) -> 'QrDisplayBrightness':
        min_diff: int|None = None
        for e in cls:
            if min_diff is None or abs(value - e.value) < abs(value - min_diff.value):
                min_diff = e
        return min_diff


class Language(Choice):
    ENGLISH = 'en'
    # CHINESE_SIMPLIFIED = 'zh_Hans_CN'
    # CHINESE_TRADITIONAL = 'zh_Hant_TW'
    FRENCH = 'fr'
    ITALIAN = 'it'
    # JAPANESE = 'jp'
    # KOREAN = 'kr'
    PORTUGUESE = 'pt'
    DUTCH = 'nl'
    GERMAN = 'de'
    RUSSIAN = 'ru'
    CZECH = 'cs'
    SPANISH = 'es'
    LOJBAN = 'lojban'
    ESPERANTO = 'eo'

    @property
    def language(self) -> SeedLanguage:
        return SeedLanguage.fromCode(self.value)

    @property
    def english_name(self) -> str:
        return self.language.englishName

    @property
    def name(self) -> str:
        return self.language.name

    @property
    def is_monero(self) -> bool:
        return self.language.supported(SeedType.MONERO)

    @property
    def is_polyseed(self) -> bool:
        return self.language.supported(SeedType.POLYSEED)

    @classmethod
    def monero(cls) -> list:
        return [l for l in cls.all() if l.is_monero]

    @classmethod
    def polyseed(cls) -> list:
        return [l for l in cls.all() if l.is_polyseed]


class XmrDenomination(Choice):

    XMR = 'XMR'
    ATOMIC_UNITS = 'pXMR'
    TRESHOLD = 'thr'
    HYBRID = 'hyb'

    @property
    def display(self) -> str:
        return {
            self.XMR: "XMR-only",
            self.ATOMIC_UNITS: "AtomicUnits-only",
            self.TRESHOLD: "Threshold at 0.01",
            self.HYBRID: "XMR | pXMR hybrid",
        }[self]


class CameraRotation(Choice):

    NONE = 0
    ROTATION_90 = 90
    ROTATION_180 = 180
    ROTATION_270 = 270

    @property
    def display(self) -> str:
        return f'{self.value}°'

    def __int__(self) -> int:
        return self.value


class QrDensity(Choice):

    LOW = 'L'
    MEDIUM = 'M'
    HIGH = 'H'


class ViewOnlyWalletFormat(Choice):

    WALLET_URI = 'U'
    JSON = 'J'


class Category(Choice):

    SYSTEM = 'system'
    DISPLAY = 'display'
    WALLET = 'wallet'
    FEATURES = 'features'


class Visibility(Choice):

    GENERAL = 'general'
    ADVANCED = 'advanced'
    HIDDEN = 'hidden'   # For data-only (e.g. custom_derivation), not configurable by the user


class Setting(Choice):
    # Individual SettingsEntry attrs
    LANGUAGE = 'language'
    MONERO_WORDLIST_LANGUAGE = 'monero_wordlist_language'
    POLYSEED_WORDLIST_LANGUAGE = 'monero_wordlist_language'
    BACKUP_TEST = 'backup_test'
    BACKUP_TEST_METHOD = 'backup_test_method'
    PERSISTENT_SETTINGS = 'persistent_settings'
    XMR_DENOMINATION = 'denomination'

    LOW_SECURITY = 'low_security'
    VIEW_WALLET_QR_FORMAT = 'wallet_qr_format'
    NETWORKS = 'networks'
    QR_DENSITY = 'qr_density'
    SIG_TYPES = 'sig_types'
    MONERO_SEED_PASSPHRASE = 'monero_seed_passphrase'
    POLYSEED_PASSPHRASE = 'polyseed_passphrase'
    CAMERA_ROTATION = 'camera_rotation'
    COMPACT_SEEDQR = 'compact_seedqr'
    MESSAGE_SIGNING = 'message_signing'
    PRIVACY_WARNINGS = 'privacy_warnings'
    DIRE_WARNINGS = 'dire_warnings'
    QR_BRIGHTNESS_TIPS = 'qr_brightness_tips'
    PARTNER_LOGOS = 'partner_logos'

    DEBUG = 'debug'

    # Hidden settings
    QR_BRIGHTNESS = 'qr_background_color'


class Type(Choice):

    ENABLED_DISABLED = 'enabled_disabled'
    ENABLED_DISABLED_PROMPT = 'enabled_disabled_prompt'
    ENABLED_DISABLED_PROMPT_REQUIRED = 'enabled_disabled_prompt_required'
    SELECT_1 = 'select_1'
    MULTISELECT = 'multiselect'

class PersistentSettings:
    SD_INSERTED_HELP_TEXT = 'Store Settings on SD card'
    SD_REMOVED_HELP_TEXT = 'Insert SD card to enable'


@dataclass
class SettingsEntry:
    """
    Defines all the parameters for a single settings entry.

    * category: Mostly for organizational purposes when displaying options in the
        SettingsQR UI. Potentially an additional sub-level breakout in the menus
        on the device itself, too.

    * selection_options: May be specified as a list[any] or list[tuple[any, str]].
        The tuple form is to provide a human-readable display_name. Probably all
        entries should shift to using the tuple form.
    """
    category: Category
    attr: Setting
    display_name: str
    abbreviated_name: str|None = None
    visibility: Visibility = Visibility.GENERAL
    type: Type = Type.ENABLED_DISABLED
    help_text: str|None = None
    selection_options: list[SelectionOption]|None = None
    default_value: list[SelectionOption]|SelectionOption|str|int|None = None

    def __post_init__(self):
        if self.abbreviated_name is None:
            self.abbreviated_name = self.attr.value
        if self.type == Type.ENABLED_DISABLED:
            self.selection_options = [Option.ENABLED, Option.DISABLED]

        elif self.type == Type.ENABLED_DISABLED_PROMPT:
            self.selection_options = [Option.ENABLED, Option.DISABLED, Option.PROMPT]

        elif self.type == Type.ENABLED_DISABLED_PROMPT_REQUIRED:
            self.selection_options = Option.all()

    @property
    def selection_options_display_names(self) -> list[str]:
        if isinstance(self.selection_options[0], SelectionOption):
            return [v.display for v in self.selection_options]
        if type(self.selection_options[0]) == tuple:
            return [v[1] for v in self.selection_options]
        # Always return a copy so the original can't be altered
        return list(self.selection_options)

    def get_selection_option_value(self, i: int) -> str|int|None:
        """ Returns the value of the selection option at index `i` """
        if i >= len(self.selection_options):
            return None
        value = self.selection_options[i]
        if type(value) == tuple:
            value = value[0]
        return value

    def get_selection_option_display_name_by_value(self, value) -> str:
        for option in self.selection_options:
            if type(option) == tuple:
                option_value = option[0]
                display_name = option[1]
            else:
                option_value = option
                display_name = option
            if option_value == value:
                return display_name

    def get_selection_option_value_by_display_name(self, display_name: str):
        for option in self.selection_options:
            if type(option) == tuple:
                option_value = option[0]
                option_display_name = option[1]
            else:
                option_value = option
                option_display_name = option
            if option_display_name == display_name:
                return option_value

    def to_dict(self) -> dict:
        if self.selection_options:
            selection_options = []
            for option in self.selection_options:
                if type(option) == tuple:
                    value = option[0]
                    display_name = option[1]
                else:
                    display_name = option
                    value = option
                selection_options.append({
                    "display_name": display_name,
                    "value": value
                })
        else:
            selection_options = None

        return {
            "category": self.category,
            "attr": self.attr.value,
            "abbreviated_name": self.abbreviated_name,
            "display_name": self.display_name,
            "visibility": self.visibility,
            "type": self.type,
            "help_text": self.help_text,
            "selection_options": selection_options,
            "default_value": self.default_value,
        }


class SettingsDefinition:
    """
    Master list of all settings, their possible options, their defaults, on-device
    display strings, and enriched SettingsQR UI options.

    Used to auto-build the Settings UI menuing with no repetitive boilerplate code.

    Defines the on-disk persistent storage structure and can read that format back
    and validate the values.

    Used to generate a master json file that documents all these params which can
    then be read in by the SettingsQR UI to auto-generate the necessary html inputs.
    """
    # Increment if there are any breaking changes; write migrations to bridge from
    # incompatible prior versions.
    version: int = 1

    settings_entries: list[SettingsEntry] = [
        # General options
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.LANGUAGE,
            abbreviated_name="lang",
            display_name="Language",
            type=Type.SELECT_1,
            visibility=Visibility.HIDDEN,  # HIDDEN/DISABLED
            selection_options=[Language.ENGLISH],
            default_value=Language.ENGLISH
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.MONERO_WORDLIST_LANGUAGE,
            abbreviated_name="m_wl_lang",
            display_name="Mnemonic language",
            type=Type.SELECT_1,
            visibility=Visibility.HIDDEN,  # HIDDEN/DISABLED
            selection_options=Language.monero(),
            default_value=Language.ENGLISH
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.POLYSEED_WORDLIST_LANGUAGE,
            abbreviated_name="ps_wl_lang",
            display_name="Polyseed language",
            type=Type.SELECT_1,
            visibility=Visibility.HIDDEN,  # HIDDEN/DISABLED
            selection_options=Language.polyseed(),
            default_value=Language.ENGLISH
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.BACKUP_TEST,
            abbreviated_name="bckup_test",
            display_name="Backup Test",
            type=Type.SELECT_1,
            selection_options=Option.required(),
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.BACKUP_TEST_METHOD,
            abbreviated_name="bckup_test_method",
            display_name="Backup Test Method",
            type=Type.SELECT_1,
            selection_options=BackupTestMethod.all(),
            default_value=BackupTestMethod.PARTIAL
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.PERSISTENT_SETTINGS,
            abbreviated_name="persistent",
            display_name="Persistent settings",
            help_text=PersistentSettings.SD_INSERTED_HELP_TEXT,
            default_value=Option.DISABLED
        ),
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.XMR_DENOMINATION,
            display_name="Denomination display",
            abbreviated_name="denom",
            type=Type.SELECT_1,
            selection_options=XmrDenomination.all(),
            default_value=XmrDenomination.TRESHOLD
        ),
        # Advanced options
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.VIEW_WALLET_QR_FORMAT,
            display_name="Wallet QR Format",
            abbreviated_name="wqrfmt",
            type=Type.MULTISELECT,
            visibility=Visibility.ADVANCED,
            selection_options=ViewOnlyWalletFormat.all(),
            default_value=[ViewOnlyWalletFormat.WALLET_URI]
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.NETWORKS,
            display_name="Monero networks",
            type=Type.MULTISELECT,
            visibility=Visibility.ADVANCED,
            selection_options=Network.all(),
            default_value=[Network.MAIN]
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.QR_DENSITY,
            display_name="QR code density",
            type=Type.SELECT_1,
            visibility=Visibility.ADVANCED,
            selection_options=QrDensity.all(),
            default_value=QrDensity.MEDIUM
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.MONERO_SEED_PASSPHRASE,
            display_name="Monero seed passphrase",
            type=Type.SELECT_1,
            selection_options=Option.required(),
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.POLYSEED_PASSPHRASE,
            display_name="Polyseed passphrase",
            type=Type.SELECT_1,
            visibility=Visibility.ADVANCED,
            selection_options=Option.required(),
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.CAMERA_ROTATION,
            abbreviated_name="camera",
            display_name="Camera rotation",
            type=Type.SELECT_1,
            visibility=Visibility.ADVANCED,
            selection_options=CameraRotation.all(),
            default_value=CameraRotation.ROTATION_180
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.COMPACT_SEEDQR,
            display_name="CompactSeedQR",
            visibility=Visibility.ADVANCED,
            default_value=Option.DISABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.MESSAGE_SIGNING,
            display_name="Message signing",
            visibility=Visibility.HIDDEN,
            default_value=Option.DISABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.PRIVACY_WARNINGS,
            abbreviated_name="priv_warn",
            display_name="Show privacy warnings",
            visibility=Visibility.ADVANCED,
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.LOW_SECURITY ,
            abbreviated_name="low_sec",
            display_name="Low security",
            visibility=Visibility.ADVANCED,
            default_value=Option.DISABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.DIRE_WARNINGS,
            abbreviated_name="dire_warn",
            display_name="Show dire warnings",
            visibility=Visibility.ADVANCED,
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.QR_BRIGHTNESS_TIPS,
            display_name="Show QR brightness tips",
            visibility=Visibility.ADVANCED,
            default_value=Option.ENABLED
        ),
        SettingsEntry(
            category=Category.FEATURES,
            attr=Setting.PARTNER_LOGOS,
            abbreviated_name="partners",
            display_name="Show partner logos",
            visibility=Visibility.HIDDEN,
            default_value=Option.ENABLED
        ),
        # "Hidden" settings with no UI interaction
        SettingsEntry(
            category=Category.SYSTEM,
            attr=Setting.QR_BRIGHTNESS,
            abbreviated_name="qr_brightness",
            display_name="QR background color",
            type=Type.SELECT_1,
            selection_options=QrDisplayBrightness.all(),
            visibility=Visibility.HIDDEN,
            default_value=QrDisplayBrightness.DEFAULT
        ),
    ]

    @classmethod
    def get_settings_entries(cls, visibility: Visibility = Visibility.GENERAL) -> list[SettingsEntry]:
        return [e for e in cls.settings_entries if e.visibility == visibility]

    @classmethod
    def get_settings_entry_by_abbreviated_name(cls, abbreviated_name: str) -> SettingsEntry:
        for entry in cls.settings_entries:
            if abbreviated_name == entry.abbreviated_name:
                return entry

    @classmethod
    def get_settings_entry(cls, attr: Setting) -> SettingsEntry:
        for entry in cls.settings_entries:
            if entry.attr == attr:
                return entry

    @classmethod
    def get_defaults(cls) -> dict[Setting, list[str|int]|str|int]:
        # Must copy the default_value list, otherwise we'll inadvertently change
        # defaults when updating these attrs
        return {
            e.attr: e.default_value if type(e) != list else e.default_value.copy()
            for e in cls.settings_entries
        }

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "settings_entries": [e.to_dict() for e in cls.settings_entries],
        }


if __name__ == "__main__":
    from json import dump
    from os import uname

    hostname = uname()[1]
    if hostname == "xmrsigner-os":
        output_file = "/mnt/microsd/settings_definition.json"
    else:
        output_file = "settings_definition.json"
    with open(output_file, 'w') as json_file:
        dump(SettingsDefinition.to_dict(), json_file, indent=4)
