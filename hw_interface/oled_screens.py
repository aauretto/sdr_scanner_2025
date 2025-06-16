from hw_interface import hw_enums
from hw_interface.font_manager import FontManager
from enum import Enum, auto

class Screens(Enum):
    SETTINGS = auto()
    FREQTUNE = auto()
    VOLUME   = auto()

import time



_FONT_MANAGER = FontManager()


# =============================================================================
# Screens to display
# =============================================================================
def draw_tuning_window(draw, meta):
        draw.line((0, 26, 128, 26), fill="white")
        freq = f"{meta['cf'] / 1e6:09.4f}"
        mhz = "MHz"
        freqFt = _FONT_MANAGER.load_font(18, isNumber=True)
        mhzFt  = _FONT_MANAGER.load_font(8)

        # Welcome to magic numberville. Putting things in here that look ok in the real world
        render_text_and_cursor(meta, draw, (13,36), freqFt, 7, 2, freq, 4, 1)
        draw.text((94, 45), mhz, font = mhzFt, fill="white")

        # Sig Strength
        dB = meta['dB']
        sign = "-" if dB < 0 else ""
        render_right_justified_text(draw, (123, 5), f"{sign}{abs(dB):05.2f}", font=_FONT_MANAGER.load_font(8))
        render_right_justified_text(draw, (113, 15), "dB", font=_FONT_MANAGER.load_font(8))
        draw.line((78, 0, 78, 26), fill="white")

        is_dst = time.localtime().tm_isdst
        draw.text((9, 5), time.strftime("%H:%M", time.localtime()), font=_FONT_MANAGER.load_font(8), fill="white")
        draw.text((15, 15), time.tzname[is_dst], font=_FONT_MANAGER.load_font(8), fill="white")
        draw.line((50, 0, 50, 26), fill="white")

        draw.text((55, 9), "FM", font=_FONT_MANAGER.load_font(10), fill="white")


# =============================================================================
# Utility Functions
# =============================================================================
def render_right_justified_text(draw, topRight, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tH = bbox[3] - bbox[1]
    tW = bbox[2] - bbox[0]

    draw.text((topRight[0] - tW, topRight[1]), text, font=font, fill="white")

def render_text_and_cursor(meta, draw, startPos, font, charWidth, kerning, text, decimalWid, cursorSpacing):
    render_text_monospace(draw, startPos, font, charWidth, kerning, text, decimalWid)
    bbox = draw.textbbox((0, 0), text, font=font)
    tH = bbox[3] - bbox[1]

    # Draw Cursor:
    x = startPos[0] - 1 + meta["cursorPos"] * (charWidth + kerning) + (meta["cursorPos"] >= 4) * (decimalWid + kerning) 
    y = startPos[1] + tH + cursorSpacing + 4 # More magic numbers to make the math work
    draw.line((x, y, x + charWidth - kerning // 2, y), fill="white") 

def render_text_monospace(draw, startPos, font, charWidth, kerning, text, decimalWid):
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
