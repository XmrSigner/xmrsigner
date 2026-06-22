from random import uniform, choice
from time import time, sleep
from PIL import Image

from xmrsigner.gui.constants import Padding
from xmrsigner.gui.components import Fonts, Theme, load_image
from xmrsigner.gui.screens.screen import BaseScreen
from xmrsigner.models.settings import (
    Settings,
    Setting,
    Option
)


# TODO: This early code is now outdated vis-a-vis Screen vs View distinctions
class LogoScreen(BaseScreen):

    def __init__(self):
        super().__init__()
        self.logo = load_image('logo_black_240.png')
        self.partners = [
            'monero_ccs',
        ]
        self.partner_logos: dict[str, Image.Image]  = {
            partner: load_image(f'partner_{partner}_logo.png')
            for partner in self.partners
        }

    def get_random_partner(self) -> str:
        return choice(self.partners)


class OpeningSplashScreen(LogoScreen):

    def start(self):
        from xmrsigner.controller import Controller
        controller: Controller = Controller.get_instance()
        show_partner_logos: bool = Settings.get_instance().get_value(Setting.PARTNER_LOGOS) == Option.ENABLED
        logo_offset_y = -56 if show_partner_logos else 0
        # Fade in alpha
        for i in range(250, -1, -25):
            self.logo.putalpha(255 - i)
            background = Image.new('RGBA', size=self.logo.size, color=Theme.BACKGROUND_COLOR)
            self.renderer.canvas.paste(Image.alpha_composite(background, self.logo), (0, logo_offset_y))
            self.renderer.show_image()
        # Display version num below XmrSigner logo
        font = Fonts.get_font(Theme.BODY_FONT_NAME, Theme.TOP_NAV_TITLE_FONT_SIZE)
        version = f'v{controller.VERSION}'
        (left, top, version_tw, version_th) = font.getbbox(version, anchor='lt')
        # The logo png is 240x240, but the actual logo is 70px tall, vertically centered
        version_x = int(self.renderer.canvas_width - 35)  # changed it to the right border for the new logo
        version_y = int(self.canvas_height / 2) + 35 + logo_offset_y + Padding.COMPONENT
        self.renderer.draw.text(xy=(version_x, version_y), text=version, font=font, fill=Theme.VERSION_COLOR, anchor='rt')  # changed from middle top (mt) to right top (rt) for the new logo
        self.renderer.show_image()
        if show_partner_logos:
            # Hold on the version num for a moment
            sleep(1)
            # Set up the partner logo
            partner_logo: Image.Image = self.partner_logos[self.get_random_partner()]
            font = Fonts.get_font(Theme.TOP_NAV_TITLE_FONT_NAME, Theme.BODY_FONT_SIZE)
            sponsor_text = 'With support from:'
            (left, top, tw, th) = font.getbbox(sponsor_text, anchor='lt')
            x = int((self.renderer.canvas_width) / 2)
            y = self.canvas_height - Padding.COMPONENT - partner_logo.height - int(Padding.COMPONENT/2) - th
            self.renderer.draw.text(xy=(x, y), text=sponsor_text, font=font, fill='#ccc', anchor='mt')
            self.renderer.canvas.paste(
                partner_logo,
                (
                    int((self.renderer.canvas_width - partner_logo.width) / 2),
                    y + th + int(Padding.COMPONENT/2)
                )
            )
            self.renderer.show_image()
        sleep(5)


class ScreensaverScreen(LogoScreen):

    def __init__(self, buttons):
        super().__init__()
        self.buttons = buttons
        # Paste the logo in a bigger image that is 2x the size of the logo
        self.image = Image.new("RGB", (2 * self.logo.size[0], 2 * self.logo.size[1]), (0,0,0))
        self.image.paste(self.logo, (int(self.logo.size[0] / 2), int(self.logo.size[1] / 2)))
        self.min_coords = (0, 0)
        self.max_coords = (self.logo.size[0], self.logo.size[1])
        self.increment_x = self.rand_increment()
        self.increment_y = self.rand_increment()
        self.cur_x = int(self.logo.size[0] / 2)
        self.cur_y = int(self.logo.size[1] / 2)
        self._is_running = False
        self.last_screen = None

    @property
    def is_running(self):
        return self._is_running

    def rand_increment(self):
        max_increment = 10.0
        min_increment = 1.0
        increment = uniform(min_increment, max_increment)
        if uniform(-1.0, 1.0) < 0.0:
            return -1.0 * increment
        return increment


    def start(self):
        if self.is_running:
            return

        self._is_running = True

        # Store the current screen in order to restore it later
        self.last_screen = self.renderer.canvas.copy()

        screensaver_start = int(time() * 1000)

        # Screensaver must block any attempts to use the Renderer in another thread so it
        # never gives up the lock until it returns.
        with self.renderer.lock:
            try:
                while self._is_running:
                    if self.buttons.has_any_input() or self.buttons.override_ind:
                        break
                    # Must crop the image to the exact display size
                    crop = self.image.crop((
                        self.cur_x, self.cur_y,
                        self.cur_x + self.renderer.canvas_width, self.cur_y + self.renderer.canvas_height))
                    self.renderer.disp.ShowImage(crop, 0, 0)

                    self.cur_x += self.increment_x
                    self.cur_y += self.increment_y

                    # At each edge bump, calculate a new random rate of change for that axis
                    if self.cur_x < self.min_coords[0]:
                        self.cur_x = self.min_coords[0]
                        self.increment_x = self.rand_increment()
                        if self.increment_x < 0.0:
                            self.increment_x *= -1.0
                    elif self.cur_x > self.max_coords[0]:
                        self.cur_x = self.max_coords[0]
                        self.increment_x = self.rand_increment()
                        if self.increment_x > 0.0:
                            self.increment_x *= -1.0

                    if self.cur_y < self.min_coords[1]:
                        self.cur_y = self.min_coords[1]
                        self.increment_y = self.rand_increment()
                        if self.increment_y < 0.0:
                            self.increment_y *= -1.0
                    elif self.cur_y > self.max_coords[1]:
                        self.cur_y = self.max_coords[1]
                        self.increment_y = self.rand_increment()
                        if self.increment_y > 0.0:
                            self.increment_y *= -1.0
                    sleep(0.05)
            except KeyboardInterrupt as e:
                # Exit triggered; close gracefully
                print("Shutting down Screensaver")

                # Have to let the interrupt bubble up to exit the main app
                raise e
            finally:
                self._is_running = False
                # Restore the original screen
                self.renderer.show_image(self.last_screen)

    def stop(self):
        self._is_running = False
