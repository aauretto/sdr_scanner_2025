"""
Definitions for the demodulaiton functions to be used by the scanner.
"""
import numpy as np
from enum import Enum, auto
from scipy.signal import butter, lfilter
import param_types as ptys
from collections import deque


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
        self.__currDecoding = DemodSchemes.AM
        self.__normBuffer = deque(maxlen=8)
        self.AMnormFactor = 1
        # self.amLpNum, self.amLpDenom = butter(5, (20e3 / 2) / (0.5 * 0.25e6), btype='low', analog=False)
        self.__fxs = {
            DemodSchemes.FM : self.DECODE_FM,
            DemodSchemes.AM : self.DECODE_AM,
        }
    
    def DECODE_FM(self, sig, **meta):
        """
        According to the internet this approximates differentiating phase...
        """
        diff = np.angle(sig[1:] * np.conj(sig[:-1]))
        return diff / np.pi

    def DECODE_AM(self, sig, **meta):
        rawDemod = np.abs(sig)
        
        # Normalize
        self.__normBuffer.append(rawDemod.max())
        return rawDemod / np.mean(list(self.__normBuffer)) * self.AMnormFactor
        # Quiet any high-frequency products of demodulating
        # return lfilter(self.amLpNum, self.amLpDenom, rawDemod)
    

    def set_demod_scheme(self, key):
        if key not in self.__fxs:
            print(f"Invalid Decoding Scheme {key}. Please use any of {self.__fxs.keys()}")
        self.__currDecoding = key
        print(f"New demod is now: {self.__currDecoding}")

    def get_demod_scheme_name(self):
        return str(self.__currDecoding).split(".")[1]

    def cycle_decoding_scheme(self, step = 1):
        schemes = list(self.__fxs.keys())
        next = (schemes.index(self.__currDecoding) + step) % len(schemes)
        self.set_demod_scheme(schemes[next])


    def __call__(self, *args, **kwargs):
        return self.__fxs[self.__currDecoding](*args, **kwargs)
    
    def create_filter(self, bw, fs):
        """
        Squirreled this function away here since its tangentially related to demodulating the input
        rf.
        """
        print(f"Making new filter for {bw = } and {fs = }")
        num, denom = butter(5, (bw / 2) / (0.5 * fs), btype='low', analog=False)
        return (num, denom)
