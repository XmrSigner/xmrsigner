from enum import StrEnum

class Color(StrEnum):

    BLACK = '#000000'
    BLACK_FADED = '#2C2C2C'
    WHITE = '#FFFFFF'
    WHITE_FADED = '#FCFCFC'
    WHITE_DARK = '#E8E8E8'
    YELLOW = '#FFD60A'
    RED = '#FF0000'
    RED_FADED = '#FF453A'
    GREEN = '#30D158'
    GREEN_PASTEL = '#00F1CA'
    BLUE = '#0000FF'
    BLUE_PASTEL = '#00CAF1'
    PURPLE = '#FF00FF'
    MONERO_ORANGE = '#ED5F00'
    MONERO_ORANGE_FADED = "#F06D36"
    GRAY = '#777777'
    GRAY_DARKER = '#666666'
    GRAY_LIGHT = '#909090'
    GRAY_LIGHTER = '#C0C0C0'
    GRAY_DARK = '#303030'

    def __str__(self) -> str:
        return self.value

    @property
    def r(self) -> int:
        return int.from_bytes(bytes.fromhex(self.value[1:3]))

    @property
    def g(self) -> int:
        return int.from_bytes(bytes.fromhex(self.value[3:5]))

    @property
    def b(self) -> int:
        return int.from_bytes(bytes.fromhex(self.value[5:7]))


class Padding:
    EDGE = 8
    COMPONENT = 8
    LIST_ITEM = 4


class Font(StrEnum):
    AWESOME = 'Font_Awesome_6_Free-Solid-900'
    ICON = 'xmrsigner-icons'
    OPEN_SANS_SEMI_BOLD = 'OpenSans-SemiBold'
    OPEN_SANS_REGULAR = 'OpenSans-Regular'
    INCONSOLATA_REGULAR = 'Inconsolata-Regular'
    INCONSOLATA_SEMI_BOLD = 'Inconsolata-SemiBold'
    ROBOTO_CONDENSED_BOLD = 'RobotoCondensed-Bold'

    def __str__(self) -> str:
        return self.value


class FontAwesome:
    ANGLE_DOWN = '\uf107'
    ANGLE_LEFT = '\uf104'
    ANGLE_RIGHT = '\uf105'
    ANGLE_UP = '\uf106'
    CAMERA = '\uf030'
    CARET_DOWN = '\uf0d7'
    CARET_LEFT = '\uf0d9'
    CARET_RIGHT = '\uf0da'
    CARET_UP = '\uf0d8'
    SOLID_CIRCLE_CHECK = '\uf058'
    CIRCLE = '\uf111'
    CIRCLE_CHEVRON_RIGHT = '\uf138'
    DICE = '\uf522'
    DICE_ONE = '\uf525'
    DICE_TWO = '\uf528'
    DICE_THREE = '\uf527'
    DICE_FOUR = '\uf524'
    DICE_FIVE = '\uf523'
    DICE_SIX = '\uf526'
    GEAR = '\uf013'
    KEY = '\uf084'
    KEYBOARD = '\uf11c'
    LOCK = '\uf023'
    MAP = '\uf279'
    PAPER_PLANE = '\uf1d8'
    PEN = '\uf304'
    PLUS = '+'
    POWER_OFF = '\uf011'
    ROTATE_RIGHT = '\uf2f9'
    SCREWDRIVER_WRENCH = '\uf7d9'
    SQUARE = '\uf0c8'
    SQUARE_CARET_DOWN = '\uf150'
    SQUARE_CARET_LEFT = '\uf191'
    SQUARE_CARET_RIGHT = '\uf152'
    SQUARE_CARET_UP = '\uf151'
    SQUARE_CHECK = '\uf14a'
    TRIANGLE_EXCLAMATION = '\uf071'
    UNLOCK = '\uf09c'
    QRCODE = '\uf029'
    X = '\u0058'
    WALLET = '\uf555'
    TRASH_CAN = '\uf2ed'
    VAULT = '\ue2c5'
    LIST = '\uf03a'
    SEEDLING = '\uf4d8'
    EYE = '\uf06e'
    EYE_LIGHT = '\uf06e'
    COINS = '\uf51e'
    CONVERT = '\uf30b'
    CHEVRON_UP = '\uf077'
    CHEVRON_DOWN = '\uf078'


class Icon:
    # Menu icons
    SCAN = '\ue900'
    SEEDS = '\ue901'
    SETTINGS = '\ue902'
    TOOLS = '\ue903'

    # Utility icons
    BACK = '\ue904'
    CHECK = '\ue905'
    CHECKBOX = '\ue906'
    CHECKBOX_SELECTED = '\ue907'
    CHEVRON_DOWN = '\ue908'
    CHEVRON_LEFT = '\ue909'
    CHEVRON_RIGHT = '\ue90a'
    CHEVRON_UP = '\ue90b'
    CLOSE = '\ue90c'
    PAGE_DOWN = '\ue90d'
    PAGE_UP = '\ue90e'
    PLUS = '\ue90f'
    POWER = '\ue910'
    RESTART = '\ue911'

    # Messaging icons
    ERROR = '\ue912'
    SUCCESS = '\ue913'
    WARNING = '\ue914'

    # Informational icons
    ADDRESS = '\ue915'
    CHANGE = '\ue916'
    DERIVATION = '\ue917'
    FEE = '\ue918'
    FINGERPRINT = '\ue919'
    PASSPHRASE = '\ue91a'

    # Misc icons
    MONERO = '\ue91b'  # TODO: don't need BTC, need XMR glyph is still Bitcoin
    MONERO_ALT = '\ue91c'  # TODO: don't need BTC, need XMR glyph is still Bitcoin
    BRIGHTNESS = '\ue91d'
    MICROSD = '\ue91e'
    QRCODE = '\ue91f'

    MIN_VALUE = SCAN
    MAX_VALUE = QRCODE
