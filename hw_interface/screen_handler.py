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
        self.__fonts = {}
        self.load_font(24),
        self.load_font(16),
        self.load_font(12),
        self.load_font(8)

    def load_font(self, pt):
        if pt not in self.__fonts:
            self.__fonts[pt] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", pt)
        return self.__fonts[pt]

    def draw_frame(self, meta, menuState):
        with canvas(self.__device) as draw:
            draw.rectangle((0, 0, 127, 63), outline=1, fill=0)

            self.draw_tuning_window(draw, meta)

            time.sleep(self.__SECS_PER_FRAME)

    def draw_tuning_window(self, draw, meta):
        draw.line((0, 26, 128, 26), fill="white")
        freq = f"{meta[hw_enums.Menus.FREQTUNE]['cf']:09.4f}"
        mhz = "MHz"
        freqFt = self.load_font(18)
        mhzFt  = self.load_font(8)

        draw.text((5, 36), freq, font = freqFt, fill="white")
        draw.text((103, 45), mhz, font = mhzFt, fill="white")

        # Draw Cursor:
        x = 5 + meta[hw_enums.Menus.FREQTUNE]["cursorPos"] * 11 + (meta[hw_enums.Menus.FREQTUNE]["cursorPos"] >= 4) * 6
        y = 55
        draw.line((x, y, x + 10, y), fill="white") 

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