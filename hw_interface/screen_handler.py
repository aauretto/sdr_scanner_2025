from luma.core.interface.serial import spi
from luma.oled.device import ssd1309
from luma.core.render import canvas
from PIL import Image, ImageFont
import RPi.GPIO as GPIO
import time
# import hw_interface.runner.HWMenuManager.Menus as Menus
from hw_interface import hw_enums

GPIO.setwarnings(False)

class ScreenDrawer():

    def __init__(self):        
        self.__FRAME_RATE = 30
        self.__SECS_PER_FRAME = 1/self.__FRAME_RATE
        self.__serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=8_000_000)
        self.__device = ssd1309(self.__serial, width=128, height=64)
        self.__running = True

        # Font stuff
        self.__alphaFonts = {}
        self.__numFonts = {}
        self.load_font(24),
        self.load_font(16),
        self.load_font(12),
        self.load_font(8)

    def load_font(self, pt, isNumber = False):
        if isNumber:
            if pt not in self.__numFonts:
                # self.__numFonts[pt] = ImageFont.truetype("~/Documents/sdr_scanner_2025/hw_interface/fonts/seven_segment.ttf", pt)
                self.__numFonts[pt] = ImageFont.truetype("./hw_interface/fonts/seven_segment.ttf", pt)
            return self.__numFonts[pt]
        else:
            if pt not in self.__alphaFonts:
                if pt <= 16:
                    self.__alphaFonts[pt] = ImageFont.truetype("./hw_interface/fonts/pixel_operator8.ttf", pt)
                else:
                    self.__alphaFonts[pt] = ImageFont.truetype("./hw_interface/fonts/pixel_operator_bold.ttf", pt)
            return self.__alphaFonts[pt]
        

    def draw_frame(self, meta, menuState):
        with canvas(self.__device) as draw:
            draw.rectangle((0, 0, 127, 63), outline=1, fill=0)

            self.draw_tuning_window(draw, meta)

            time.sleep(self.__SECS_PER_FRAME)

    def draw_tuning_window(self, draw, meta):
        draw.line((0, 26, 128, 26), fill="white")
        freq = f"{meta[hw_enums.Menus.FREQTUNE]['cf']:09.4f}"
        mhz = "MHz"
        freqFt = self.load_font(18, isNumber=True)
        mhzFt  = self.load_font(8)

        # Welcome to magic numberville. Putting things in here that look ok in the real world
        self.render_text_and_cursor(meta, draw, (13,36), freqFt, 7, 2, freq, 4, 1)
        draw.text((94, 45), mhz, font = mhzFt, fill="white")

    def render_text_and_cursor(self, meta, draw, startPos, font, charWidth, kerning, text, decimalWid, cursorSpacing):
        self.render_text_monospace(draw, startPos, font, charWidth, kerning, text, decimalWid)
        bbox = draw.textbbox((0, 0), text, font=font)
        tH = bbox[3] - bbox[1]

        # Draw Cursor:
        x = startPos[0] - 1 + meta[hw_enums.Menus.FREQTUNE]["cursorPos"] * (charWidth + kerning) + (meta[hw_enums.Menus.FREQTUNE]["cursorPos"] >= 4) * (decimalWid + kerning) 
        y = startPos[1] + tH + cursorSpacing + 4 # More magic numbers to make the math work
        draw.line((x, y, x + charWidth - kerning // 2, y), fill="white") 

    def render_text_monospace(self, draw, startPos, font, charWidth, kerning, text, decimalWid):
        """
        Will render a string as monospace even if supplied font is not monospace. Exception for the '.' char
        which has width decimalWid and is centered.
        Usage: Displaying numbers that will be interacted with in menus with a cursor / underscore
        """
        x, y = startPos
        frontPad = 0
        bbox = draw.textbbox((0, 0), text, font=font)
        cH = bbox[3] - bbox[1]

        for i, char in enumerate(text):
            
            if char == ".":
                # Gross math to make decimal not mono
                left   = x + frontPad + decimalWid // 2 - 1
                top    = y + cH + 1
                right  = x + frontPad + decimalWid // 2
                bottom = y + cH + 2
                draw.rectangle((left, top, right, bottom), fill = "white")
                frontPad += decimalWid + kerning
                continue

            bbox = draw.textbbox((0, 0), char, font=font)
            cW = bbox[2] - bbox[0]
            draw.text((x + frontPad + charWidth - cW, y), char, font=font, fill="white")
            frontPad += charWidth + kerning


    def run(self, meta, menuState):
        while self.__running:
            self.draw_frame(meta, menuState)

    def stop(self):
        self.__running = False

def __testing():
    sd = ScreenDrawer()
    sd.run()


if __name__ == "__main__":
    __testing()