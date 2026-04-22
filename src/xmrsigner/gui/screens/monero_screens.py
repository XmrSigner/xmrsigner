from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFilter
from xmrsigner.helpers.pillow import get_font_size
from time import sleep
from datetime import date, timedelta
from calendar import monthrange

from ots.enums import Network
from ots.ots import Ots
from xmrsigner.gui.renderer import Renderer
from xmrsigner.models.threads import BaseThread

from xmrsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from xmrsigner.hardware.buttons import (
    HardwareButtonsConstants,
    HardwareButtons
)
from xmrsigner.gui.screens.screen import (
    ButtonListScreen,
    WarningScreen,
    BaseTopNavScreen
)
from xmrsigner.gui.components import (
    XmrAmount,
    BaseComponent,
    Button,
    CheckboxButton,
    Icon,
    FontAwesomeIconConstants,
    IconTextLine,
    FormattedAddress,
    GUIConstants,
    Fonts,
    IconConstants,
    TextArea,
    calc_bezier_curve,
    linear_interp
)


@dataclass
class TxOverviewScreen(ButtonListScreen):
    spend_amount: int = 0
    change_amount: int = 0
    fee_amount: int = 0
    num_inputs: int = 0
    num_self_transfer_outputs: int = 0
    num_change_outputs: int = 0
    destination_addresses: list[str] = None


    def __post_init__(self):
        # Customize defaults
        self.title = "Review Transaction"
        self.is_bottom_list = True
        self.button_data = ["Review Details"]

        # This screen can take a while to load while parsing the Tx
        self.show_loading_screen = True

        super().__post_init__()

        # Prep the headline amount being spent in large callout
        # icon_text_lines_y = self.components[-1].screen_y + self.components[-1].height
        icon_text_lines_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING

        if not self.destination_addresses:
            # This is a self-transfer
            spend_amount = self.change_amount
        else:
            spend_amount = self.spend_amount

        self.components.append(
            XmrAmount(
                total_atomic_units=spend_amount,
                screen_y=icon_text_lines_y,
                font_size=20
            )
        )

        # Prep the transaction flow chart
        self.chart_x = 0
        self.chart_y = self.components[-1].screen_y + self.components[-1].height + int(GUIConstants.COMPONENT_PADDING/2)
        chart_height = self.buttons[0].screen_y - self.chart_y - GUIConstants.COMPONENT_PADDING

        # We need to supersample the whole panel so that small/thin elements render
        # clearly.
        ssf = 4  # super-sampling factor

        # Set up our temp supersampled rendering surface
        image = Image.new(
            "RGB",
            (self.canvas_width * ssf, chart_height * ssf),
            GUIConstants.BACKGROUND_COLOR
        )
        draw = ImageDraw.Draw(image)

        font_size = GUIConstants.BODY_FONT_MIN_SIZE * ssf
        font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, font_size)

        (left, top, right, bottom) = font.getbbox(text="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890[]", anchor="lt")
        chart_text_height = bottom
        vertical_center = int(image.height/2)
        # Supersampling renders thin elements poorly if they land on an even line before scaling down
        if vertical_center % 2 == 1:
            vertical_center += 1

        association_line_color = "#666"
        association_line_width = 3*ssf
        curve_steps = 4
        chart_font_color = "#ddd"
        # First calculate how wide the inputs col will be
        inputs_column = []
        if self.num_inputs == 1:
            inputs_column.append("1 input")
        elif self.num_inputs > 5:
            inputs_column.append("input 1")
            inputs_column.append("input 2")
            inputs_column.append("[ ... ]")
            inputs_column.append(f"input {self.num_inputs-1}")
            inputs_column.append(f"input {self.num_inputs}")
        else:
            for i in range(0, self.num_inputs):
                inputs_column.append(f"input {i+1}")

        max_inputs_text_width = 0
        for input in inputs_column:
            tw, th = get_font_size(font, input)
            max_inputs_text_width = max(tw, max_inputs_text_width)

        # Given how wide we want our curves on each side to be...
        curve_width = 4*GUIConstants.COMPONENT_PADDING*ssf

        # ...and the minimum center divider width...
        center_bar_width = 2*GUIConstants.COMPONENT_PADDING*ssf

        # We can calculate how wide the destination col can be
        max_destination_col_width = image.width - (GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + \
            int(GUIConstants.COMPONENT_PADDING*ssf/4) + curve_width + \
                center_bar_width + \
                    curve_width + int(GUIConstants.COMPONENT_PADDING*ssf/4) + \
                        GUIConstants.EDGE_PADDING*ssf)
        # if self.num_inputs == 1:
        #     # Use up more of the space on the input side
        #     max_destination_col_width += curve_width

        # Now let's maximize the actual destination col by adjusting our addr truncation
        def calculate_destination_col_width(truncate_at: int = 0):
            def truncate_destination_addr(addr):
                if len(addr) <= truncate_at + len("..."):
                    # No point in truncating
                    return addr
                return f"{addr[:truncate_at]}..."
            destination_column = []
            if len(self.destination_addresses) + self.num_self_transfer_outputs <= 3:
                for addr in self.destination_addresses:
                    destination_column.append(truncate_destination_addr(addr))
                for i in range(0, self.num_self_transfer_outputs):
                    destination_column.append(truncate_destination_addr("self-transfer"))
            else:
                # destination_column.append(f"{len(self.destination_addresses)} recipients")
                destination_column.append(f"recipient 1")
                destination_column.append(f"[ ... ]")
                destination_column.append(f"recipient {len(self.destination_addresses) + self.num_self_transfer_outputs}")

            destination_column.append(f"fee")

            if self.num_change_outputs > 0:
                for i in range(0, self.num_change_outputs):
                    destination_column.append("change")

            max_destination_text_width = 0
            for destination in destination_column:
                tw, th = get_font_size(font, destination)
                max_destination_text_width = max(tw, max_destination_text_width)
            return (max_destination_text_width, destination_column)
        if len(self.destination_addresses) + self.num_self_transfer_outputs > 3:
            # We're not going to display any destination addrs so truncation doesn't matter
            (destination_text_width, destination_column) = calculate_destination_col_width()
        else:
            # Steadliy widen out the destination column until we run out of space
            for i in range(6, 14):
                (new_width, new_col_text) = calculate_destination_col_width(truncate_at=i)
                if new_width > max_destination_col_width:
                    break
                destination_text_width = new_width
                destination_column = new_col_text

        destination_col_x = image.width - (destination_text_width + GUIConstants.EDGE_PADDING*ssf)

        # Now we can finalize our center bar values
        center_bar_x = GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4) + curve_width

        # Center bar stretches to fill any excess width
        center_bar_width = destination_col_x - int(GUIConstants.COMPONENT_PADDING*ssf/4) - curve_width - center_bar_x

        # Position each input row
        num_rendered_inputs = len(inputs_column)
        if self.num_inputs == 1:
            inputs_y = vertical_center - int(chart_text_height/2)
            inputs_y_spacing = 0  # Not used
        else:
            inputs_y = int((image.height - num_rendered_inputs*chart_text_height) / (num_rendered_inputs + 1))
            inputs_y_spacing = inputs_y + chart_text_height

        # Don't render lines from an odd number
        if inputs_y % 2 == 1:
            inputs_y += 1
        if inputs_y_spacing % 2 == 1:
            inputs_y_spacing += 1

        inputs_conjunction_x = center_bar_x
        inputs_x = GUIConstants.EDGE_PADDING*ssf

        input_curves = []
        for input in inputs_column:
            # Calculate right-justified input display
            tw, th = get_font_size(font, input)
            cur_x = inputs_x + max_inputs_text_width - tw
            draw.text(
                (cur_x, inputs_y),
                text=input,
                font=font,
                fill=chart_font_color,
                anchor="lt",
            )

            # Render the association line to the conjunction point
            # First calculate a bezier curve to an inflection point
            start_pt = (
                inputs_x + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4),
                inputs_y + int(chart_text_height/2)
            )
            conjunction_pt = (inputs_conjunction_x, vertical_center)
            mid_pt = (
                int(start_pt[0]*0.5 + conjunction_pt[0]*0.5),
                int(start_pt[1]*0.5 + conjunction_pt[1]*0.5)
            )

            if len(inputs_column) == 1:
                # Use fewer segments for single input straight line
                bezier_points = [
                    start_pt,
                    linear_interp(start_pt, conjunction_pt, 0.33),
                    linear_interp(start_pt, conjunction_pt, 0.66),
                    conjunction_pt
                ]
            else:
                bezier_points = calc_bezier_curve(
                    start_pt,
                    (mid_pt[0], start_pt[1]),
                    mid_pt,
                    curve_steps
                )
                # We don't need the "final" point as it's repeated below
                bezier_points.pop()

                # Now render the second half after the inflection point
                bezier_points += calc_bezier_curve(
                    mid_pt,
                    (mid_pt[0], conjunction_pt[1]),
                    conjunction_pt,
                    curve_steps
                )

            input_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            inputs_y += inputs_y_spacing
        # Render center bar
        draw.line(
            (
                center_bar_x,
                vertical_center,
                center_bar_x + center_bar_width,
                vertical_center
            ),
            fill=association_line_color,
            width=association_line_width
        )

        # Position each destination
        num_rendered_destinations = len(destination_column)
        if num_rendered_destinations == 1:
            destination_y = vertical_center - int(chart_text_height/2)
            destination_y_spacing = 0
        else:
            destination_y = int((image.height - num_rendered_destinations*chart_text_height) / (num_rendered_destinations + 1))
            destination_y_spacing = destination_y + chart_text_height

        # Don't render lines from an odd number
        if destination_y % 2 == 1:
            destination_y += 1
        if destination_y_spacing % 2 == 1:
            destination_y_spacing += 1

        destination_conjunction_x = center_bar_x + center_bar_width
        recipients_text_x = destination_col_x

        output_curves = []
        for destination in destination_column:
            draw.text(
                (recipients_text_x, destination_y),
                text=destination,
                font=font,
                fill=chart_font_color,
                anchor="lt"
            )

            # Render the association line from the conjunction point
            # First calculate a bezier curve to an inflection point
            conjunction_pt = (destination_conjunction_x, vertical_center)
            end_pt = (
                conjunction_pt[0] + curve_width,
                destination_y + int(chart_text_height/2)
            )
            mid_pt = (
                int(conjunction_pt[0]*0.5 + end_pt[0]*0.5),
                int(conjunction_pt[1]*0.5 + end_pt[1]*0.5)
            )
            bezier_points = calc_bezier_curve(
                conjunction_pt,
                (mid_pt[0], conjunction_pt[1]),
                mid_pt,
                curve_steps
            )
            # We don't need the "final" point as it's repeated below
            bezier_points.pop()

            # Now render the second half after the inflection point
            curve_bias = 1.0
            bezier_points += calc_bezier_curve(
                mid_pt,
                (int(mid_pt[0]*curve_bias + end_pt[0]*(1.0-curve_bias)), end_pt[1]),
                end_pt,
                curve_steps
            )

            output_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            destination_y += destination_y_spacing

        # Resize to target and sharpen final image
        image = image.resize((self.canvas_width, chart_height), Image.LANCZOS)
        self.paste_images.append((image.filter(ImageFilter.SHARPEN), (self.chart_x, self.chart_y)))

        # Pass input and output curves to the animation thread
        self.threads.append(
            TxOverviewScreen.TxExplorerAnimationThread(
                inputs=input_curves,
                outputs=output_curves,
                supersampling_factor=ssf,
                offset_y=self.chart_y,
                renderer=self.renderer
            )
        )



    class TxExplorerAnimationThread(BaseThread):
        def __init__(self, inputs, outputs, supersampling_factor, offset_y, renderer: Renderer):
            super().__init__()

            # Translate the point coords into renderer space
            ssf = supersampling_factor
            self.inputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in inputs]
            self.outputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in outputs]
            self.renderer = renderer


        def run(self):
            pulse_color = GUIConstants.ACCENT_COLOR
            reset_color = "#666"
            line_width = 3

            pulses = []

            # The center bar needs to be segmented to support animation across it
            start_pt = self.inputs[0][-1]
            end_pt = self.outputs[0][0]
            if start_pt == end_pt:
                # In single input the center bar width can be zeroed out.
                # Ugly hack: Insert this line segment that will be skipped otherwise.
                center_bar_pts = [end_pt, self.outputs[0][1]]
            else:
                center_bar_pts = [
                    start_pt,
                    linear_interp(start_pt, end_pt, 0.25),
                    linear_interp(start_pt, end_pt, 0.50),
                    linear_interp(start_pt, end_pt, 0.75),
                    end_pt,
                ]

            def draw_line_segment(curves, i, j, color):
                # print(f"draw: {curves[0][i]} to {curves[0][j]}")
                for points in curves:
                    pt1 = points[i]
                    pt2 = points[j]
                    self.renderer.draw.line(
                        (pt1[0], pt1[1], pt2[0], pt2[1]),
                        fill=color,
                        width=line_width
                    )

            prev_color = reset_color
            while self.keep_running:
                with self.renderer.lock:
                    # Only generate one new pulse at a time; trailing "reset_color" pulse
                    # erases the most recent pulse.
                    if not pulses or (
                        prev_color == pulse_color and pulses[-1][0] == 10):
                        # Create a new pulse
                        if prev_color == pulse_color:
                            pulses.append([0, reset_color])
                        else:
                            pulses.append([0, pulse_color])
                        prev_color = pulses[-1][1]

                    for pulse_num, pulse in enumerate(pulses):
                        i = pulse[0]
                        color = pulse[1]
                        if i < len(self.inputs[0]) - 1:
                            # We're in the input curves
                            draw_line_segment(self.inputs, i, i+1, color)
                        elif i < len(self.inputs[0]) + len(center_bar_pts) - 2:
                            # We're in the center bar
                            index = i - len(self.inputs[0]) + 1
                            draw_line_segment([center_bar_pts], index, index+1, color)
                        elif i < len(self.inputs[0]) + len(center_bar_pts) - 2 + len(self.outputs[0]) - 1:
                            index = i - (len(self.inputs[0]) + len(center_bar_pts) - 2)
                            draw_line_segment(self.outputs, index, index+1, color)
                        else:
                            # This pulse is done
                            del pulses[pulse_num]
                            continue

                        pulse[0] += 1

                    self.renderer.show_image()

                # No need to CPU limit when running in its own thread?
                sleep(0.02)



@dataclass
class TxMathScreen(ButtonListScreen):

    input_amount: int = 0
    num_inputs: int = 0
    spend_amount: int = 0
    num_recipients: int = 0
    fee_amount: int = 0
    change_amount: int = 0


    def __post_init__(self):
        # Customize defaults
        self.title = "Tx Math"
        self.button_data = ["Review Recipients"]
        self.is_bottom_list = True

        super().__post_init__()

        if self.input_amount > 10**10:
            denomination = "xmr"
            self.input_amount /= 10**12
            self.spend_amount /= 10**12
            self.change_amount /= 10**12
            self.input_amount = f"{self.input_amount:,.12f}"
            self.spend_amount = f"{self.spend_amount:,.12f}"
            self.change_amount = f"{self.change_amount:,.12f}"

            # Note: We keep the fee denominated in atomic units; just left pad it so it still
            # lines up properly.
            self.fee_amount = f"{self.fee_amount:10}"
        else:
            denomination = "pXMR"
            self.input_amount = f"{self.input_amount:,}"
            self.spend_amount = f"{self.spend_amount:,}"
            self.fee_amount = f"{self.fee_amount:,}"
            self.change_amount = f"{self.change_amount:,}"

        longest_amount = max(len(self.input_amount), len(self.spend_amount), len(self.fee_amount), len(self.change_amount))
        if len(self.input_amount) < longest_amount:
            self.input_amount = " " * (longest_amount - len(self.input_amount)) + self.input_amount

        if len(self.spend_amount) < longest_amount:
            self.spend_amount = " " * (longest_amount - len(self.spend_amount)) + self.spend_amount

        if len(self.fee_amount) < longest_amount:
            self.fee_amount = " " * (longest_amount - len(self.fee_amount)) + self.fee_amount

        if len(self.change_amount) < longest_amount:
            self.change_amount = " " * (longest_amount - len(self.change_amount)) + self.change_amount

        # Render the info to temp Image
        body_width = self.canvas_width - 2 * GUIConstants.EDGE_PADDING
        body_height = self.buttons[0].screen_y - self.top_nav.height - 2 * GUIConstants.COMPONENT_PADDING
        ssf = 2  # Super-sampling factor
        image = Image.new("RGB", (body_width*ssf, body_height*ssf))
        draw = ImageDraw.Draw(image)

        body_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, (GUIConstants.BODY_FONT_SIZE) * ssf)
        fixed_width_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, (GUIConstants.BODY_FONT_SIZE + 6) * ssf)
        digits_width, digits_height = get_font_size(fixed_width_font, self.input_amount + "+")

        # Draw each line of the equation
        cur_y = 0

        def render_amount(cur_y, amount_str, info_text, info_text_color=GUIConstants.BODY_FONT_COLOR):
            secondary_digit_color = "#888"
            tertiary_digit_color = "#666"
            digit_group_spacing = 2 * ssf
            # secondary_digit_color = GUIConstants.BODY_FONT_COLOR
            # tertiary_digit_color = GUIConstants.BODY_FONT_COLOR
            # digit_group_spacing = 0
            if denomination == 'xmr':
                display_str = amount_str
                main_zone = display_str[:-6]
                mid_zone = display_str[-6:-3]
                end_zone = display_str[-3:]
                main_zone_width, th = get_font_size(fixed_width_font, main_zone)
                mid_zone_width, th = get_font_size(fixed_width_font, end_zone)
                draw.text((0, cur_y), text=main_zone, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
                draw.text((main_zone_width + digit_group_spacing, cur_y), text=mid_zone, font=fixed_width_font, fill=secondary_digit_color)
                draw.text((main_zone_width + digit_group_spacing + mid_zone_width + digit_group_spacing, cur_y), text=end_zone, font=fixed_width_font, fill=tertiary_digit_color)
            else:
                draw.text((0, cur_y), text=amount_str, font=fixed_width_font, fill=GUIConstants.BODY_FONT_COLOR)
            draw.text((digits_width + 2*digit_group_spacing, cur_y), text=info_text, font=body_font, fill=info_text_color)

        render_amount(
            cur_y,
            f" {self.input_amount}",
            # info_text=f""" {self.num_inputs} input{"s" if self.num_inputs > 1 else ""}""",
            info_text=f""" input{"s" if self.num_inputs > 1 else ""}""",
        )

        # spend_amount will be zero on self-transfers; only display when there's an
        # external recipient.
        if self.num_recipients > 0:
            cur_y += int(digits_height * 1.2)
            render_amount(
                cur_y,
                f"-{self.spend_amount}",
                # info_text=f""" {self.num_recipients} recipient{"s" if self.num_recipients > 1 else ""}""",
                info_text=f""" recipient{"s" if self.num_recipients > 1 else ""}""",
            )

        cur_y += int(digits_height * 1.2)
        render_amount(
            cur_y,
            f"-{self.fee_amount}",
            info_text=f""" fee""",
        )

        cur_y += int(digits_height * 1.2) + 4 * ssf
        draw.line((0, cur_y, image.width, cur_y), fill=GUIConstants.BODY_FONT_COLOR, width=1)
        cur_y += 8 * ssf

        render_amount(
            cur_y,
            f" {self.change_amount}",
            info_text=f" {denomination} change",
            info_text_color="darkorange"  # super-sampling alters the perceived color
        )

        # Resize to target and sharpen final image
        image = image.resize((body_width, body_height), Image.LANCZOS)
        self.paste_images.append((image.filter(ImageFilter.SHARPEN), (GUIConstants.EDGE_PADDING, self.top_nav.height + GUIConstants.COMPONENT_PADDING)))



@dataclass
class TxAddressDetailsScreen(ButtonListScreen):
    address: str = None
    amount: int = 0

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True

        super().__post_init__()

        center_img_height = self.buttons[0].screen_y - self.top_nav.height

        # Figuring out how to vertically center the sats and the address is
        # difficult so we just render to a temp image and paste it in place.
        center_img = Image.new("RGB", (self.canvas_width, center_img_height), GUIConstants.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(center_img)

        xmr_amount = XmrAmount(
            image_draw=draw,
            canvas=center_img,
            total_atomic_units=self.amount,
            screen_y=int(GUIConstants.COMPONENT_PADDING/2),
            font_size=20
        )

        formatted_address = FormattedAddress(
            image_draw=draw,
            canvas=center_img,
            width=self.canvas_width - 2*GUIConstants.EDGE_PADDING,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=xmr_amount.height + GUIConstants.COMPONENT_PADDING,
            font_size=24,
            address=self.address,
        )

        # Render each to the temp img we passed in
        xmr_amount.render()
        formatted_address.render()
        self.body_img = center_img.crop((
            0,
            0,
            self.canvas_width,
            formatted_address.screen_y + formatted_address.height
        ))
        body_img_y = self.top_nav.height + int((center_img_height - self.body_img.height - GUIConstants.COMPONENT_PADDING)/2)
        self.paste_images.append((self.body_img, (0, body_img_y)))


@dataclass
class TxChangeDetailsScreen(ButtonListScreen):
    title: str = 'Your Change'
    amount: int = 0
    address: str = None
    fingerprint: str = None
    is_polyseed: bool = False
    is_my_monero: bool = False
    is_change_derivation_path: bool = True
    derivation_path_addr_index: int = 0
    is_change_addr_verified: bool = False

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()
        self.components.append(XmrAmount(
            total_atomic_units=self.amount,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            font_size=20
        ))
        self.components.append(FormattedAddress(
            screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            address=self.address,
            max_lines=1,
        ))
        screen_y = self.components[-1].screen_y + self.components[-1].height + 2 * GUIConstants.COMPONENT_PADDING
        self.components.append(IconTextLine(
            icon_name=IconConstants.FINGERPRINT,
            icon_color=GUIConstants.FINGERPRINT_POLYSEED_COLOR if self.is_polyseed else GUIConstants.FINGERPRINT_MONERO_SEED_COLOR if not self.is_my_monero else GUIConstants.FINGERPRINT_MY_MONERO_SEED_COLOR,
            value_text=f"""{self.fingerprint}: {"Change" if self.is_change_derivation_path else "Addr"} #{self.derivation_path_addr_index}""",
            is_text_centered=False,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=screen_y,
        ))
        if self.is_change_addr_verified:
            self.components.append(IconTextLine(
                icon_name=IconConstants.SUCCESS,
                icon_color=GUIConstants.SUCCESS_COLOR,
                value_text="Address verified!",
                is_text_centered=False,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=self.components[-1].screen_y + self.components[-1].height + GUIConstants.COMPONENT_PADDING,
            ))


@dataclass
class TxFinalizeScreen(ButtonListScreen):

    def __post_init__(self):
        # Customize defaults
        self.title = "Sign Tx"
        self.is_bottom_list = True
        super().__post_init__()

        icon = Icon(
            icon_name=FontAwesomeIconConstants.PAPER_PLANE,
            icon_color=GUIConstants.INFO_COLOR,
            icon_size=GUIConstants.ICON_LARGE_BUTTON_SIZE,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        icon.screen_x = int((self.canvas_width - icon.width) / 2)
        self.components.append(icon)

        self.components.append(TextArea(
            text="Click to authorize this transaction",
            screen_y=icon.screen_y + icon.height + GUIConstants.COMPONENT_PADDING
        ))


@dataclass
class DateOrBlockHeightScreen(BaseTopNavScreen):

    network: Network = Network.MAIN
    is_block_height: bool = False
    focus: BaseComponent|None = None
    focusable_elements: list[BaseComponent] = None
    current_height: int = 0
    current_date: date = date.today()

    def __post_init__(self):
        self.title = 'Block Height'
        if not self.is_block_height and self.current_height != 0:
            self.current_date = date.fromtimestamp(Ots.timestampFromHeight(self.current_height, self.network))
        if self.is_block_height and  self.current_date != date.today():
            self.current_height = Ots.heightFromTimestamp(int(self.current_date), self.network)
        super().__post_init__()

    def _render(self):
        super()._render()
        self.components = []
        self.renderer.show_image()

    def _run(self):
        # Start the interactive update loop
        KEYMAP = {
            HardwareButtonsConstants.KEY1: self.key_btn_1,
            HardwareButtonsConstants.KEY2: self.key_btn_2,
            HardwareButtonsConstants.KEY3: self.key_btn_3,
            HardwareButtonsConstants.KEY_PRESS: self.key_press,
            HardwareButtonsConstants.KEY_UP: self.key_up,
            HardwareButtonsConstants.KEY_DOWN: self.key_down,
            HardwareButtonsConstants.KEY_LEFT: self.key_left,
            HardwareButtonsConstants.KEY_RIGHT: self.key_right
        }
        self.create_common()
        self.create_block_height()
        self.create_date()
        if self.is_block_height:
            self.focus = self.btn_block_height[0]
        else:
            self.focus = self.year
        while True:
            self.calc_focusable_elements()
            self.components.append(self.top_nav)
            self.render_common()
            if self.is_block_height:
                self.render_block_height()
            else:
                self.render_date()
            self._render()
            input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.ALL_KEYS,
                check_release=True
                )
            # Check possible exit conditions
            if self.top_nav.is_selected and input == HardwareButtonsConstants.KEY_PRESS:
                return RET_CODE__BACK_BUTTON
            if input in KEYMAP:
                ret: str|None = KEYMAP[input]()
                if ret:
                    return ret
                continue

    def key_up(self) -> None:
        if self.focus in self.btn_block_height or self.focus in [self.year, self.month, self.day]:
            self.key_increase_or_decrease(True)
            # self.focus = self.btn_height if not self.is_block_height else self.btn_date
            return
        if self.focus == self.btn_accept:
            self.focus = self.btn_block_height[0] if self.is_block_height else self.year
            return
        if self.focus in [self.btn_height, self.btn_date]:
            self.focus = None
            self.top_nav.is_selected = True
            return

    def key_down(self) -> None:
        if self.focus in self.btn_block_height or self.focus in [self.year, self.month, self.day]:
            self.key_increase_or_decrease(False)
            # self.focus = self.btn_accept
            return
        if self.focus in [self.btn_height, self.btn_date]:
            self.focus = self.btn_block_height[0] if self.is_block_height else self.year
            return
        if self.top_nav.is_selected:
            self.top_nav.is_selected = False
            self.focus = self.btn_height if self.is_block_height else self.btn_date
            return

    def key_left(self) -> None:
        if self.focus == self.btn_accept:
            self.focus = self.btn_block_height[7] if self.is_block_height else self.day
            return
        if self.focus in self.btn_block_height:
            pos = (self.btn_block_height.index(self.focus) - 1)
            if pos < 0:
                self.focus = self.btn_height
                return
            self.focus = self.btn_block_height[pos]
            return
        fields = [self.year, self.month, self.day]
        if self.focus in fields:
            pos = (fields.index(self.focus) - 1)
            if pos < 0:
                self.focus = self.btn_height
                return
            self.focus = fields[pos]
            return
        if self.focus == self.btn_height:
            self.focus = self.btn_date
            return
        if self.focus == self.btn_date:
            self.focus = None
            self.top_nav.is_selected = True
            return

    def key_right(self) -> None:
        if self.focus in self.btn_block_height:
            pos = (self.btn_block_height.index(self.focus) + 1)
            if pos > 7:
                self.focus = self.btn_accept
                return
            self.focus = self.btn_block_height[pos]
            return
        fields = [self.year, self.month, self.day]
        if self.focus in fields:
            pos = (fields.index(self.focus) + 1)
            if pos > 2:
                self.focus = self.btn_accept
                return
            self.focus = fields[pos]
            return
        if self.focus == self.btn_height:
            self.focus = self.btn_block_height[0] if self.is_block_height else self.year
            return
        if self.focus == self.btn_date:
            self.focus = self.btn_height
            return
        if self.focus is None and self.top_nav.is_selected:
            self.top_nav.is_selected = False
            self.focus = self.btn_date

    def key_press(self) -> str|None:
        if self.focus == self.btn_accept or self.focus in self.btn_block_height or self.focus in [self.year, self.month, self.day]:
            if not self.is_block_height:
                self.current_height = Ots.heightFromTimestamp(int(self.current_date - timedelta(days=30)), self.network)
            return f'{self.current_height:08d}'
        if self.focus in [self.btn_height, self.btn_date]:
            self.set_block_height_selection(self.focus == self.btn_height)
            return

    def key_btn_1(self) -> None:  # increase
        self.key_increase_or_decrease(True)

    def key_btn_2(self) -> None:
        self.set_block_height_selection(self.is_block_height ^ True)

    def key_btn_3(self) -> None:  # decrease
        self.key_increase_or_decrease(False)

    def key_increase_or_decrease(self, increase: bool = True) -> None:
        modifier: int = 1 if increase else -1
        if self.focus in [self.year, self.month, self.day]:
            self.current_date = date(
                max((self.current_date.year + (modifier if self.year==self.focus else 0)) % 2300, 2014),
                max((self.current_date.month + (modifier if self.month==self.focus else 0)) % 13, 1),
                max((self.current_date.day + (modifier if self.day==self.focus else 0)) % (monthrange(self.current_date.year, self.current_date.month)[1] + 1), 1)
            )
            return
        if self.focus in self.btn_block_height:
            digits = list(f'{self.current_height:08d}')
            pos = self.btn_block_height.index(self.focus)
            digits[pos] = str((int(digits[pos]) + modifier) % 10)
            self.current_height = int(''.join(digits))
            return

    def set_block_height_selection(self, block_height: bool) -> None:
        self.is_block_height = block_height
        if block_height:
            self.current_height = Ots.heightFromTimestamp(int(self.current_date), self.network)
            self.focus = self.btn_block_height[0]
        else:
            self.current_date = date.fromtimestamp(Ots.timestampFromHeight(self.current_height, self.network))
            self.focus = self.year

    def create_common(self) -> None:
        self.btn_date = Button(
            text='Date',
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.top_nav.height + GUIConstants.EDGE_PADDING,
            width=int(self.canvas_width // 2) - GUIConstants.EDGE_PADDING - GUIConstants.COMPONENT_PADDING,
        )
        self.btn_height = Button(
            text='Height',
            screen_x=int(self.canvas_width // 2) + (GUIConstants.COMPONENT_PADDING // 2),
            screen_y=self.top_nav.height + GUIConstants.EDGE_PADDING,
            width=int(self.canvas_width // 2) - GUIConstants.EDGE_PADDING - (GUIConstants.COMPONENT_PADDING // 2),
        )
        self.arrow_up = Icon(
            icon_name=FontAwesomeIconConstants.CARET_UP,
            icon_color=GUIConstants.ACCENT_COLOR,
            icon_size=GUIConstants.ICON_FONT_SIZE,
            screen_y=0
        )
        self.arrow_down = Icon(
            icon_name=FontAwesomeIconConstants.CARET_DOWN,
            icon_color=GUIConstants.ACCENT_COLOR,
            icon_size=GUIConstants.ICON_FONT_SIZE,
            screen_y=0,
            screen_x=0
        )
        self.btn_accept = Button(
            text='Accept',
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=0,
            width=self.canvas_width - GUIConstants.EDGE_PADDING * 2
        )
        self.btn_accept.screen_y=self.canvas_height - GUIConstants.EDGE_PADDING - self.btn_accept.height

    def create_block_height(self) -> None:
        self.btn_block_height_width = int((self.canvas_width - GUIConstants.EDGE_PADDING * 2 - GUIConstants.COMPONENT_PADDING * 7) // 8)
        self.btn_block_height: list[Button] = []
        for pos in range(8):
            self.btn_block_height.append(Button(
                text='0',
                screen_x=GUIConstants.EDGE_PADDING + pos * (self.btn_block_height_width + GUIConstants.COMPONENT_PADDING),
                screen_y=int(self.canvas_height // 2),
                width=self.btn_block_height_width
            ))

    def calc_focusable_elements(self) -> None:
        self.focusable_elements = [self.btn_date, self.btn_height]
        for btn in self.btn_block_height if self.is_block_height else [self.year, self.month, self.day]:
            self.focusable_elements.append(btn)
        self.focusable_elements.append(self.btn_accept)

    def render_common(self) -> None:
        self.btn_date.is_selected = self.focus == self.btn_date
        self.btn_date.outline_color = GUIConstants.ACCENT_COLOR if not self.is_block_height else None
        self.components.append(self.btn_date)
        self.btn_height.is_selected = self.focus == self.btn_height
        self.btn_height.outline_color = GUIConstants.ACCENT_COLOR if self.is_block_height else None
        self.components.append(self.btn_height)
        self.btn_accept.is_selected = self.focus == self.btn_accept
        self.components.append(self.btn_accept)
        if self.focus in self.btn_block_height or self.focus in [self.year, self.month, self.day]:
            self.arrow_up.screen_y = self.focus.screen_y - self.arrow_up.height + GUIConstants.COMPONENT_PADDING // 4
            self.arrow_up.screen_x = int(self.focus.screen_x + self.focus.width / 2 - self.arrow_up.width / 2 + 0.5)
            self.components.append(self.arrow_up)
            self.arrow_down.screen_y = self.focus.screen_y + self.focus.height + self.arrow_up.height - GUIConstants.COMPONENT_PADDING
            self.arrow_down.screen_x = int(self.focus.screen_x + self.focus.width / 2 - self.arrow_down.width / 2 + 0.5)
            self.components.append(self.arrow_down)

    def render_block_height(self) -> None:
        digits = f'{self.current_height:08d}'
        for button in self.btn_block_height:
            button.text = digits[self.btn_block_height.index(button)]
            button.is_selected = (button == self.focus)
            button.outline_color = GUIConstants.ACCENT_COLOR if button == self.focus else None
            self.components.append(button)

    def create_date(self) -> None:
        self.year = Button(
            text=f'{self.current_date.year:04d}',
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=int(self.canvas_height // 2),
            width=(self.canvas_width - GUIConstants.EDGE_PADDING * 2 - GUIConstants.COMPONENT_PADDING * 2) // 2,
        )
        self.month = Button(
            text=f'{self.current_date.month:02d}',
            screen_x=GUIConstants.EDGE_PADDING + self.year.width + GUIConstants.COMPONENT_PADDING,
            screen_y=int(self.canvas_height // 2),
            width=(self.canvas_width - GUIConstants.EDGE_PADDING * 2 - GUIConstants.COMPONENT_PADDING * 2) // 4,
        )
        self.day = Button(
            text=f'{self.current_date.day:02d}',
            screen_x=GUIConstants.EDGE_PADDING + self.year.width + GUIConstants.COMPONENT_PADDING * 2 + self.month.width,
            screen_y=int(self.canvas_height // 2),
            width=self.month.width,
        )

    def render_date(self) -> None:
        self.year.text = f'{self.current_date.year:04d}'
        self.year.is_selected = (self.focus == self.year)
        self.year.outline_color = GUIConstants.ACCENT_COLOR if self.focus == self.year else None
        self.month.text = f'{self.current_date.month:02d}'
        self.month.is_selected = (self.focus == self.month)
        self.month.outline_color = GUIConstants.ACCENT_COLOR if self.focus == self.month else None
        self.day.text = f'{self.current_date.day:02d}'
        self.day.is_selected = (self.focus == self.day)
        self.day.outline_color=GUIConstants.ACCENT_COLOR if self.focus == self.day else None
        self.components.append(self.year)
        self.components.append(self.month)
        self.components.append(self.day)
