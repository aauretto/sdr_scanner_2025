import asyncio
from sdr_scanner_2025.async_pipeline import AsyncPipeline, BasePipelineStage, AbstractWorker, SynchWindow, Endpoint
import numpy as np

# Scale factor to do for FM audio since we drift 75kHz in each dir
# deviation_hz = 75000
# scaling_factor = Fs / (2 * np.pi * deviation_hz)
# normalized = phase_diff * scaling_factor

class DecodeFM(AbstractWorker):
    def process(self, data):
        """
        According to the internet this approximates differentiating phase...
        """
        diff = np.angle(data[1:] * np.conj(data[:-1]))
        return diff / np.pi

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
    
from scipy.signal import lfilter, butter
class LowPassFilter(AbstractWorker):
    """
    Lowpass filter to isolate band of interest
    """
    def __init__(self, cutoff, fs, order=5):
        super().__init__()
        self.b, self.a = butter(order, cutoff / (0.5 * fs), btype='low', analog=False)

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
    from sdr_scanner_2025.audio_pipe_stages import RechunkArray, ReshapeArray
    from rtlsdr import RtlSdr
    from sdr_scanner_2025.speaker_manager import SpeakerManager
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

        # Set up and launch pipeline
        pipeline = AsyncPipeline(
            [ProvideRawRF(sdr, 2**18), # Make this an sdrSpec class or smth
             DecodeFM(),
             LowPassFilter(75e3, radioFS),
             Downsample(radioFS, audioFS),
             RechunkArray(audioBlockSize),
             ReshapeArray((-1,1)),
             SynchWindow(q), 
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