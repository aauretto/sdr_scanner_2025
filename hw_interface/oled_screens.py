from hw_interface import hw_enums
from hw_interface.font_manager import FontManager
from enum import Enum, auto

class Screens(Enum):
    SETTINGS = auto()
    SQUELCH  = auto()
    FREQTUNE = auto()
    VOLUME   = auto()
    DEMOD    = auto()

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
    render_text_and_cursor(draw, (13,36), freqFt, 7, 2, freq, 4, 2, 1, meta["FTUNE_cursorPos"])
    draw.text((94, 45), mhz, font = mhzFt, fill="white")

    # Sig Strength
    dB = meta['dB']
    sign = "-" if dB < 0 else ""
    render_right_justified_text(draw, (123, 5), f"{sign}{abs(dB):05.2f}", font=_FONT_MANAGER.load_font(8))
    render_right_justified_text(draw, (113, 15), "dB", font=_FONT_MANAGER.load_font(8))
    draw.line((78, 0, 78, 26), fill="white")

    elapsed = int(time.time() - meta["start_time"])
    hh, rem = divmod(elapsed, 3600)
    mm, _   = divmod(rem, 60)

    draw.text((11,15), "Time", font=_FONT_MANAGER.load_font(8), fill="white")
    draw.text((9, 5), f"{hh:02d}:{mm:02d}", font=_FONT_MANAGER.load_font(8), fill="white")
    draw.line((50, 0, 50, 26), fill="white")

    draw.text((55, 9), meta["demod_name"], font=_FONT_MANAGER.load_font(10), fill="white")

# TODO: HOIST INTO A CONSTS FILE
SQUELCH_MIN = -40
SQUELCH_MAX = 2

# Squelch screen consts
SQUELCH_BAR_PAD  = 8
SQUELCH_BAR_LEN  = 128 - 2 * SQUELCH_BAR_PAD
SQUELCH_BAR_VPOS = 32
PX_PER_DB   = SQUELCH_BAR_LEN / (SQUELCH_MAX - SQUELCH_MIN)

SQUELCH_BAR_SERIF_HEIGHT = 7
SQUELCH_BAR_METER_HEIGHT = 3
def draw_squelch_window(draw, meta):
    """
    Draws the squelch setting screen.
    TODO: I use a lot of magic numbers here
    """
    draw.line((0, 20, 127, 20), fill="white")
    draw.text((5,5), "Set Squelch", font=_FONT_MANAGER.load_font(10), fill="white")

    # Localize Sig Strength and Squelch
    squelch = meta['squelch']
    sqlSign = "-" if squelch < 0 else ""
    dB = meta['dB']
    dBSign = "-" if dB < 0 else ""

    # Draw bar indicating range for squelch
    draw.line((SQUELCH_BAR_PAD, SQUELCH_BAR_VPOS, SQUELCH_BAR_PAD + SQUELCH_BAR_LEN, SQUELCH_BAR_VPOS), fill="white")        
    draw.line((SQUELCH_BAR_PAD, SQUELCH_BAR_VPOS - SQUELCH_BAR_SERIF_HEIGHT // 2, SQUELCH_BAR_PAD, SQUELCH_BAR_VPOS + SQUELCH_BAR_SERIF_HEIGHT // 2), fill="white")        
    draw.line((SQUELCH_BAR_PAD + SQUELCH_BAR_LEN, SQUELCH_BAR_VPOS - SQUELCH_BAR_SERIF_HEIGHT // 2, SQUELCH_BAR_PAD + SQUELCH_BAR_LEN, SQUELCH_BAR_VPOS + SQUELCH_BAR_SERIF_HEIGHT // 2), fill="white")        

    squelchMeterLen = PX_PER_DB * (dB - SQUELCH_MIN)
    draw.rectangle((SQUELCH_BAR_PAD, SQUELCH_BAR_VPOS - SQUELCH_BAR_METER_HEIGHT // 2, SQUELCH_BAR_PAD + squelchMeterLen, SQUELCH_BAR_VPOS + SQUELCH_BAR_METER_HEIGHT // 2), fill = "white") 
    
    draw.rectangle((0, 45, 50, 64), outline="white")
    draw.rectangle((78, 45, 128, 64), outline="white")
    draw.text((5,51),f"{dBSign}{abs(dB):05.2f}", fill="white", font=_FONT_MANAGER.load_font(8))
    # render_text_and_cursor(draw, (81, 51), _FONT_MANAGER.load_font(8), 6, 2, f"{sqlSign}{abs(squelch):05.2f}", None, None, 2, meta["SQUELCH_cursorPos"])
    # render_right_justified_text(draw, (123,51), f"{sqlSign}{abs(squelch):05.2f}", font=_FONT_MANAGER.load_font(8))

    cursorPos = meta["SQUELCH_cursorPos"] + 1 + (meta["SQUELCH_cursorPos"] > 1)
    draw_text_with_inverted_char(draw, (81, 51), f"{sqlSign}{abs(squelch):05.2f}", cursorPos, _FONT_MANAGER.load_font(8))

    # Draw current squelch indicator
    chevXpos = SQUELCH_BAR_PAD + PX_PER_DB * (squelch - SQUELCH_MIN) - 3
    # chevXpos = SQUELCH_BAR_PAD + squelchMeterLen - 3
    chevYpos = SQUELCH_BAR_VPOS + 3
    draw.polygon([
                  (2 + chevXpos, 6 + chevYpos), 
                  (6 + chevXpos, 6 + chevYpos), 
                  (4 + chevXpos, 2 + chevYpos)
                  ], 
                  fill='white')


def draw_demod_window(draw, meta):
    """
    Draws the demodulation setting screen.
    """
    draw.line((0, 20, 127, 20), fill="white")
    draw.text((5,5), "Set Demodulaiton", font=_FONT_MANAGER.load_font(10), fill="white")

    draw.text((28, 34), f"< {meta['demod_name']} >", font=_FONT_MANAGER.load_font(16), fill="white")


# =============================================================================
# Utility Functions
# =============================================================================

def draw_text_with_inverted_char(draw, position, text, index, font):
    x, y = position
    for i, char in enumerate(text):
        # Measure width of character
        bbox = draw.textbbox((x, y), char, font=font)
        char_width = bbox[2] - bbox[0]
        char_height = bbox[3] - bbox[1]
        # char_width, char_height = draw.textsize(char, font=font)
        
        # Draw background
        if i == index:
            bg_color = "white"
            fg_color = "black"
        else:
            bg_color = "black"
            fg_color = "white"
        
        draw.rectangle([x, y, x + char_width, y + char_height], fill=bg_color)
        draw.text((x, y), char, font=font, fill=fg_color)
        x += char_width

def render_right_justified_text(draw, topRight, text, font, fill="white"):
    bbox = draw.textbbox((0, 0), text, font=font)
    tH = bbox[3] - bbox[1]
    tW = bbox[2] - bbox[0]

    draw.text((topRight[0] - tW, topRight[1]), text, font=font, fill=fill)

def render_text_and_cursor(draw, startPos, font, charWidth, kerning, text, decimalWid, decSz, cursorSpacing, cursorPos):
    render_text_monospace(draw, startPos, font, charWidth, kerning, text, decimalWid, decSz)
    bbox = draw.textbbox((0, 0), text, font=font)
    tH = bbox[3] - bbox[1]

    # Draw Cursor:
    if decimalWid != None and decSz != None:
        numdecs = sum(list(map(lambda c : c == ".", text))[0:cursorPos+1])
        x = startPos[0] - 1 + cursorPos * (charWidth + kerning) + numdecs * (decimalWid + kerning) 
    else:
        x = startPos[0] - 1 + cursorPos * (charWidth + kerning)

    y = startPos[1] + tH + cursorSpacing + 4 # More magic numbers to make the math work
    draw.line((x, y, x + charWidth - kerning // 2, y), fill="white") 

def render_text_monospace(draw, startPos, font, charWidth, kerning, text, decimalWid = None, decSz = None):
    """
    Will render a string as monospace even if supplied font is not monospace. Exception for the '.' char
    which has width decimalWid and is centered.
    Usage: Displaying numbers that will be interacted with in menus with a cursor / underscore
    """
    x, y = startPos
    frontPad = 0
    bbox = draw.textbbox((0, 0), text, font=font)
    ascent, descent = font.getmetrics()
    lineHeight = ascent + descent 
    cH = bbox[3] - bbox[1]

    for i, char in enumerate(text):
        
        if (decimalWid != None and decSz != None) and char == ".":
            # Gross math to make decimal not mono
            left   = x + frontPad + decimalWid // 2 - decSz // 2
            top    = y + cH + 1
            right  = x + frontPad + decimalWid // 2 + decSz // 2 - 1
            bottom = y + cH + decSz // 2 + 1

            if bottom < top:
                bottom = top
            if right < left:
                right = left

            draw.rectangle((left, top, right, bottom), fill = "white")
            frontPad += decimalWid + kerning
            continue

        bbox = draw.textbbox((0, 0), char, font=font)
        cW = bbox[2] - bbox[0]
        draw.text((x + frontPad + charWidth - cW, y), char, font=font, fill="white")
        frontPad += charWidth + kerning
