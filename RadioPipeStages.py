import asyncio

from AsyncPipeline import AsyncPipeline, BasePipelineStage, AbstractWorker, SynchWindow, Endpoint
import numpy as np
from queue import Queue
from threading import Thread

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
    from rtlsdr import RtlSdr
    sdr = RtlSdr()

    # Configure SDR
    sdr.sample_rate = 0.25e6   # Hz
    sdr.center_freq = 88.3e6   # Hz
    sdr.freq_correction = 60   # PPM
    sdr.gain = 'auto'

    class GenerateLists(BasePipelineStage):
        async def execute(self):
            sz = 5
            for i in range(0, 5):
                await self.outbox.put([i]*sz)
            await self.outbox.put(None)

    q = Queue()

    def worker(q, sdr):
        # Create loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set up and launch pipeline
        pipeline = AsyncPipeline(
            [ProvideRawRF(sdr, 2**18), # Make this an sdrSpec class or smth
             DecodeFM(),
             Downsample(0.25e6, 44100),
             SynchWindow(q), 
             Endpoint()]) 
        pipeline.run_pipeline()
        
        loop.close()
    t = Thread(target=worker, args = (q, sdr))
    t.start()
    
    # Retreive the data at the end of the pipeline
    while True:
        item = q.get()
        if item is None:
            break
        print(f"[Outside pipeline] > {type(item[0])}")

    t.join()

if __name__ == "__main__":
    __testing()