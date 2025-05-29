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

class RechunkArray(BasePipelineStage):
    def __init__(self, tarBlockSize):
        super().__init__()
        self.tarBlockSize = tarBlockSize
        self.partial = np.full(shape = (tarBlockSize,), fill_value=0.0, dtype=np.float32)
        self.partialLen = 0
        self.isRunning = True

    async def execute(self):
        while self.isRunning:
            await self.consume_blocksz_samples()

    async def consume_blocksz_samples(self):
        data = await self.prevStage.get_result()
        dataPos = 0
        if data is None:
            await self.outbox.put(None)
            self.isRunning = False
            return
            
        while dataPos < len(data): # More data available from last time we got data

            # Move samples into buffer
            amtToMove = min(self.tarBlockSize - self.partialLen, len(data) - dataPos)
            self.partial[self.partialLen:self.partialLen + amtToMove] = data[dataPos: dataPos + amtToMove]                
            self.partialLen += amtToMove
            dataPos += amtToMove
            
            # Send when we have enough
            if self.partialLen == self.tarBlockSize:
                await self.outbox.put(self.partial.copy())
                self.partialLen = 0

class ReshapeArray(AbstractWorker):
    def __init__(self, newShape):
        super().__init__()
        self.newShape = newShape
    def process(self, data): 
        return data.reshape(*self.newShape)

def __testing():
    from rtlsdr import RtlSdr
    from SpeakerManager import SpeakerManager
    sdr = RtlSdr()

    # Configure SDR
    sdr.sample_rate = 0.25e6   # Hz
    sdr.center_freq = 88.3e6   # Hz
    sdr.freq_correction = 60   # PPM
    sdr.gain = 'auto'

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
             Downsample(0.25e6, audioFS),
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