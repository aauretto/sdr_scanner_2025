
from PIL import ImageFont

class FontManager():

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton so that we can avoid needing to load fonts multiple times
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Font stuff
        self.__alphaFonts = {}
        self.__numFonts = {}


    def load_font(self, pt, bold = False, isNumber = False):
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
        
