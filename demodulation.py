"""
Definitions for the demodulaiton functions to be used by the scanner.
"""
import numpy as np
from enum import Enum, auto

def DECODE_FM(sig):
    """
    According to the internet this approximates differentiating phase...
    """
    diff = np.angle(sig[1:] * np.conj(sig[:-1]))
    return diff / np.pi

def DECODE_AM(sig):
    return np.abs(sig)

class DemodSchemes(Enum):
    FM = auto()
    AM = auto()

class DemodulationManager():
    """
    Proxy for a function that demodulates raw RF.
    Holds a few demodulation schemes allowing us to swap decoding strategies on
    the fly while keeping calling code unaware of the idea that this isn't actually
    a function.
    """
    def __init__(self):
        self.__currDecoding = DemodSchemes.FM
        self.__fxs = {
            DemodSchemes.FM : DECODE_FM,
            DemodSchemes.FM : DECODE_AM,
        }
    
    def set_demod_scheme(self, key):
        if key not in self.__fxs:
            print(f"Invalid Decoding Scheme {key}. Please use any of {self.__fxs.keys()}")
        self.__currDecoding = key

    def get_demod_scheme_name(self):
        return str(self.__currDecoding).split(".")[1]

    def __call__(self, *args, **kwargs):
        return self.__fxs[self.__currDecoding](*args, **kwargs)