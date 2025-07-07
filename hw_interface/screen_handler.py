from luma.core.interface.serial import spi
from luma.oled.device import ssd1309
from luma.core.render import canvas
from PIL import Image
import RPi.GPIO as GPIO
import time
from hw_interface.font_manager import FontManager
from hw_interface.oled_menu import Menu, MenuOption
from hw_interface.oled_screens import Screens, draw_tuning_window, draw_squelch_window, draw_demod_window, draw_vol_window, draw_bw_window

GPIO.setwarnings(False)

class ScreenDrawer():

    def __init__(self):        
        self.__FRAME_RATE = 16
        self.__SECS_PER_FRAME = 1/self.__FRAME_RATE
        self.__serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=8_000_000)
        self.__device = ssd1309(self.__serial, width=128, height=64)
        self.__running = True

    def draw_frame(self, meta):
        with canvas(self.__device) as draw:
            draw.rectangle((0, 0, 127, 63), outline=1, fill=0)
            
            if meta["screen"] == Screens.FREQTUNE:
                draw_tuning_window(draw, meta)
            elif meta["screen"] == Screens.SETTINGS:
                meta["settingsMenu"].draw(draw)
            elif meta["screen"] == Screens.SQUELCH:
                draw_squelch_window(draw, meta)
            elif meta["screen"] == Screens.DEMOD:
                draw_demod_window(draw, meta)
            elif meta["screen"] == Screens.VOLUME:
                draw_vol_window(draw, meta)
            elif meta["screen"] == Screens.BANDWIDTH:
                draw_bw_window(draw, meta)

            time.sleep(self.__SECS_PER_FRAME)

    def run(self, meta):
        while self.__running:
            self.draw_frame(meta)

    def stop(self):
        self.__running = False