"""
Definitions for the demodulaiton functions to be used by the scanner.
"""
import numpy as np

# Scale factor to do for FM audio since we drift 75kHz in each dir
# deviation_hz = 75000
# scaling_factor = Fs / (2 * np.pi * deviation_hz)
# normalized = phase_diff * scaling_factor

def DECODE_FM(sig):
    """
    According to the internet this approximates differentiating phase...
    """
    diff = np.angle(sig[1:] * np.conj(sig[:-1]))
    return diff / np.pi

def DECODE_AM(sig):
    return np.abs(sig)