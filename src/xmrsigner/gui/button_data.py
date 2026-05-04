from xmrsigner.gui.components import (
    GUIConstants,
    FontAwesomeIconConstants,
    IconConstants
)


class ButtonData:

    position: int|None
    label: str
    label_color: str|None
    icon_name: str|None
    icon_color: str|None
    right_icon_name: str|None

    def __init__(
        self,
        label: str,
        icon_name: str|None = None,
        icon_color: str|None = None,
        label_color: str|None = None,
        right_icon_name: str|None = None
    ):
        self.label = label
        self.icon_name = icon_name
        self.icon_color = icon_color
        self.label_color = label_color
        self.right_icon_name = right_icon_name

    def with_icon(self, icon_name: str|None) -> 'ButtonData':
        self.icon_name = icon_name
        return self

    def with_icon_color(self, icon_color: str|None) -> 'ButtonData':
        self.icon_color = icon_color
        return self

    def with_label_color(self, label_color: str|None) -> 'ButtonData':
        self.label_color = label_color
        return self

    def with_right_icon(self, right_icon_name: str|None) -> 'ButtonData':
        self.right_icon_name = right_icon_name
        return self

    @classmethod
    def fromString(cls, label: str) -> 'ButtonData':
        return cls(label)

    @classmethod
    def fromTuple(cls, data: tuple) -> 'ButtonData':
        bd = cls(data[0])
        if len(data) > 1:
            bd.icon_name = data[1]
        if len(data) > 2:
            bd.icon_color = data[2]
        if len(data) > 3:
            bd.label_color = data[3]
        if len(data) > 4:
            bd.right_icon_name = data[4]
        return bd

    @classmethod
    def ensure(cls, data: 'str|tuple|ButtonData') -> 'ButtonData':
        if isinstance(data, cls):
            return data
        if type(data) == str:
            return cls.fromString(data)
        return cls.fromTuple(data)

    def button_kwargs(
        self,
        button_list_y: int,
        button_height: int,
        scroll_y_initial_offset: int|None,
        canvas_width: int,
        text_centered: bool,
        font_name: str,
        font_size: int,
        selected_color: str,
        is_checked: bool|None = None,
    ) -> dict:
        out: dict = {
            'text': self.label,
            'icon_name': self.icon_name,
            'icon_color': self.icon_color or GUIConstants.BUTTON_FONT_COLOR,
            'is_icon_inline': True,
            'right_icon_name': self.right_icon_name,
            'screen_x': GUIConstants.EDGE_PADDING,
            'screen_y': button_list_y + self.position * (button_height + GUIConstants.LIST_ITEM_PADDING),
            'scroll_y': scroll_y_initial_offset or 0,
            'width': canvas_width - (2 * GUIConstants.EDGE_PADDING),
            'height': button_height,
            'is_text_centered': text_centered,
            'font_name': font_name,
            'font_size': font_size,
            'font_color': self.label_color or GUIConstants.BUTTON_FONT_COLOR,
            'selected_color': selected_color,
        }
        if is_checked:
            out['is_checked'] = is_checked
        return out

    @classmethod
    def DONE(cls) -> 'ButtonData':
        return cls('Done')

    @classmethod
    def NEXT(cls) -> 'ButtonData':
        return cls('Next')

    @classmethod
    def PREVIOUS(cls) -> 'ButtonData':
        return cls('Previous')

    @classmethod
    def OK(cls) -> 'ButtonData':
        return cls('OK')

    @classmethod
    def BACK(cls) -> 'ButtonData':
        return cls('Back')

    @classmethod
    def CONTINUE(cls) -> 'ButtonData':
        return cls('Continue')

    @classmethod
    def HOME(cls) -> 'ButtonData':
        return cls('Home')

    @classmethod
    def DISCARD(cls) -> 'ButtonData':
        return cls('Discard').with_label_color(GUIConstants.RED)


class FingerprintButtonData(ButtonData):

    def __init__(
        self,
        fingerprint: str,
        is_polyseed: bool = False,
        is_legacy: bool = False
    ):
        super().__init__(
            fingerprint,
            IconConstants.FINGERPRINT,
            GUIConstants.FINGERPRINT_POLYSEED_COLOR if is_polyseed else GUIConstants.FINGERPRINT_MONERO_SEED_COLOR if not is_legacy else GUIConstants.FINGERPRINT_MY_MONERO_SEED_COLOR,
            None,
            None
        )
