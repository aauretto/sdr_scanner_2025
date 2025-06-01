import asyncio
from async_pipeline import AsyncPipeline, BasePipelineStage, AbstractWorker, Endpoint, FxApplyWindow
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

from scipy.signal import resample
class Downsample(AbstractWorker):
    """
    Downsample from radio sample rate to rate that works for audio playback
    """
    def __init__(self, fromRate, toRate):
        super().__init__()
        self.fromRate = fromRate
        self.toRate = toRate

    def process(self, data):
        return resample(data, int(len(data) * self.toRate / self.fromRate))
    
from scipy.signal import lfilter
class Filter(AbstractWorker):
    """
    Apply a filter from numerator and denominator coefficients
    """
    def __init__(self, b, a):
        super().__init__()
        self.b = b
        self.a = a
    
    def process(self, data):
        return lfilter(self.b, self.a, data)
        
class ProvideRawRF(BasePipelineStage):
    def __init__(self, sdr, spb):
        super().__init__()
        self.sdr = sdr
        self.sampleStream = self.sdr.stream(num_samples_or_bytes=spb, format='samples')

    async def execute(self):
        async for chunk in self.sampleStream:
            await self.outbox.put(chunk)
        await self.outbox.put(None)

def __testing():
    from audio_pipe_stages import RechunkArray, ReshapeArray
    from scipy.signal import butter
    from rtlsdr import RtlSdr
    from speaker_manager import SpeakerManager
    from queue import Queue
    from threading import Thread
    sdr = RtlSdr()

    # Configure SDR
    sdr.sample_rate = 0.25e6   # Hz
    sdr.center_freq = 88.3e6   # Hz
    sdr.freq_correction = 60   # PPM
    sdr.gain = 'auto'

    radioFS = sdr.get_sample_rate()

    audioFS = 44100
    audioBlockSize = 2**12

    q = Queue()

    def worker(q, sdr):
        # Create loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        b, a = butter(5, 100e3 / (0.5 * sdr.get_sample_rate()), btype='low', analog=False)

        # Set up and launch pipeline
        pipeline = AsyncPipeline(
            [ProvideRawRF(sdr, 2**18), # Make this an sdrSpec class or smth
             FxApplyWindow(DECODE_FM),
             Filter(b, a),
             Downsample(radioFS, audioFS),
             RechunkArray(audioBlockSize),
             ReshapeArray((-1,1)),
             FxApplyWindow(lambda d : q.put(d)), 
             Endpoint()]) 
        pipeline.run_pipeline()
        
        loop.close()
    rx = Thread(target=worker, args = (q, sdr))

    sm = SpeakerManager(blockSize=audioBlockSize, sampRate=audioFS)
    sm.set_source(q)
    sm.init_stream()
    sm.start()

    rx.start()
    rx.join()

if __name__ == "__main__":
    __testing()