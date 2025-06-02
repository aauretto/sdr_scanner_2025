import asyncio
from async_pipeline import AsyncPipeline, BasePipelineStage, AbstractWorker, AbstractWindow, Endpoint, FxApplyWindow, FxApplyWorker
import numpy as np

class PipelineDataPackage():
    """
    Bundle of data and metadata to be sent down pipeline
    """
    def __init__(self, data = None, meta = {}):
        self.data = data
        self.meta = meta

from scipy.signal import resample
class Downsample(AbstractWorker):
    """
    Downsample from radio sample rate to rate that works for audio playback
    """
    def __init__(self, fromRate, toRate):
        super().__init__()
        self.fromRate = fromRate
        self.toRate = toRate

    def process(self, pdp):
        data = pdp.data
        pdp.data = resample(data, int(len(data) * self.toRate / self.fromRate))
        return pdp


from scipy.signal import lfilter
class Filter(AbstractWorker):
    """
    Apply a filter from numerator and denominator coefficients
    """
    def __init__(self, b, a):
        super().__init__()
        self.b = b
        self.a = a
    
    def process(self, pdp):
        pdp.data = lfilter(self.b, self.a, pdp.data)
        return pdp
        
import time
class ProvideRawRF(BasePipelineStage):
    def __init__(self, sdr, spb):
        super().__init__()
        self.sdr = sdr
        self.sampleStream = self.sdr.stream(num_samples_or_bytes=spb, format='samples')

    async def execute(self):
        async for chunk in self.sampleStream:
            pdp = PipelineDataPackage()
            pdp.data = chunk
            pdp.meta["timestamp"] = time.time()
            await self.outbox.put(pdp)
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
        pdp = await self.prevStage.get_result()
        data = pdp.data
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
                await self.outbox.put(PipelineDataPackage(data = self.partial.copy(), meta = pdp.meta))
                self.partialLen = 0

class ReshapeArray(AbstractWorker):
    def __init__(self, newShape):
        super().__init__()
        self.newShape = newShape
    def process(self, pdp):
        data = pdp.data
        pdp.data = data.reshape(*self.newShape)
        return pdp
    
class Volume(AbstractWorker):
    """
    TODO: figure out exactly how volume control should behave
    """
    def __init__(self, ref):
        pass

class CalcDecibels(AbstractWindow):
    def inspect(self, data):
        print(np.mean(20 * np.log10(np.abs(data))))





# # Old testing code. Relevant testing to be changed in main from now on
# def __testing():
#     from scipy.signal import butter
#     from rtlsdr import RtlSdr
#     from speaker_manager import SpeakerManager
#     from queue import Queue
#     from threading import Thread
#     from demodulation import DECODE_FM
#     sdr = RtlSdr()

#     # Configure SDR
#     sdr.sample_rate = 0.25e6   # Hz
#     sdr.center_freq = 88.3e6   # Hz
#     sdr.freq_correction = 60   # PPM
#     sdr.gain = 'auto'

#     radioFS = sdr.get_sample_rate()

#     audioFS = 44100
#     audioBlockSize = 2**12

#     q = Queue()

#     def worker(q, sdr):
#         # Create loop for this thread
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#         b, a = butter(5, 100e3 / (0.5 * sdr.get_sample_rate()), btype='low', analog=False)

#         # Set up and launch pipeline
#         pipeline = AsyncPipeline(
#             [ProvideRawRF(sdr, 2**18), # Make this an sdrSpec class or smth
#              FxApplyWorker(DECODE_FM),
#              Filter(b, a),
#              Downsample(radioFS, audioFS),
#              RechunkArray(audioBlockSize),
#              ReshapeArray((-1,1)),
#              FxApplyWindow(lambda d : q.put(d)), 
#              Endpoint()]) 
#         pipeline.run_pipeline()
        
#         loop.close()
#     rx = Thread(target=worker, args = (q, sdr))

#     sm = SpeakerManager(blockSize=audioBlockSize, sampRate=audioFS)
#     sm.set_source(q)
#     sm.init_stream()
#     sm.start()

#     rx.start()
#     rx.join()

# if __name__ == "__main__":
#     __testing()