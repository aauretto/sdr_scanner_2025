from AsyncPipeline import BasePipelineStage, TransformStage
import numpy as np


# Scale factor to do for FM audio since we drift 75kHz in each dir
# deviation_hz = 75000
# scaling_factor = Fs / (2 * np.pi * deviation_hz)
# normalized = phase_diff * scaling_factor



class DecodeFM(TransformStage):
    def transform(data):
        """
        According to the internet this approximates differentiating phase...
        """
        diff = np.angle(data[1:] * np.conj(data[:-1]))
        return diff / np.pi

from scipy.signal import resample
class DownsampleAudio(TransformStage):
    """
    Downsample from radio sample rate to rate that works for audio playback
    """
    def __init__(self, fromRate, toRate):
        super().__init__()
        self.fromRate = fromRate
        self.toRate = toRate

    def transform(self, data):
        return resample(data, int(len(data) * self.toRate / self.fromRate))
        
class ProvideRawRF(BasePipelineStage):

    async def generate(self):
        