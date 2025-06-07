from luma.core.interface.serial import spi
from luma.oled.device import ssd1309
from luma.core.render import canvas
from PIL import Image, ImageFont
import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False)

class ScreenDrawer():

    def __init__(self):
        self.__FRAME_RATE = 30
        self.__SECS_PER_FRAME = 1/self.__FRAME_RATE
        self.__serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=8_000_000)
        self.__device = ssd1309(self.__serial, width=128, height=64)
        self.__running = True

        self.__bitmaps = {}
        self.load_static_image("./bitmaps/boot_splash.bmp", "boot")

        self.__device.display(self.__bitmaps["boot"])

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

    def load_static_image(self, imgPath, imgName):
        image = Image.open(imgPath).convert("1")  # Convert to 1-bit B/W
        image = image.resize(self.__device.size)
        self.__bitmaps[imgName] = image
    
    def draw_frame(self):
        with canvas(self.__device) as draw:
            draw.rectangle((0, 0, 127, 63), outline=1, fill=0)

            self.draw_tuning_window(draw)

            time.sleep(self.__SECS_PER_FRAME)

    def draw_tuning_window(self, draw):
        draw.line((0, 26, 128, 26), fill="white")
        freq = f"{88.3:08.3f}"
        mhz = "MHz"
        freqFt = self.load_font(20)
        mhzFt  = self.load_font(8)

        draw.text((5, 34), freq, font = freqFt, fill="white")
        draw.text((103, 45), mhz, font = mhzFt, fill="white")

    def run(self):
        while self.__running:
            self.draw_frame()



def __testing():
    sd = ScreenDrawer()
    sd.run()


if __name__ == "__main__":
    __testing()