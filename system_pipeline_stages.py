"""
Class definitions for rf decoding pipeline

All stages are assuming that data looks like a PipelineDatPackage object

"""

import asyncio
from pc_model import pc_runner, BaseConsumer, BaseProducer, FxApplyWindow, FxApplyWorker, AbstractWorker, AbstractWindow
import numpy as np

class PipelineDataPackage():
    """
    Bundle of data and metadata to be sent down pipeline
    """
    def __init__(self, data = None, meta = {}):
        self.data = data
        self.meta = meta

class DemodulateRF(AbstractWindow):
    """
    Perform some demodulation based on function passed to constructor
    """
    def __init__(self, dmgr):
        super().__init__()
        self.dmgr = dmgr

    def inspect(self, pdp):
        if not pdp.meta["squelched"]:
            print("AMMING")
            pdp.data = self.dmgr(pdp.data, **pdp.meta)

        pdp.meta["demod"] = self.dmgr.get().get_demod_scheme_name() # So much for being agnostic of whats in here

class Endpoint(BaseConsumer):
    """
    Black hole that eats objects from previous node's queue. Prevents last queue from growing w/o bound
    """
    async def consume(self):
        await self.source.get_result()

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
class ProvideRawRF(BaseProducer):
    def __init__(self, sdr, spb):
        super().__init__()
        self.sdr = sdr
        self.sampleStream = self.sdr.stream(num_samples_or_bytes=spb, format='samples')

    async def produce(self):
        async for chunk in self.sampleStream:
            pdp = PipelineDataPackage()
            pdp.data = chunk
            pdp.meta["timestamp"] = time.time()
            await self.outbox.put(pdp)
        await self.outbox.put(None)

class RechunkArray(BaseProducer, BaseConsumer):
    def __init__(self, tarBlockSize):
        super().__init__()
        self.tarBlockSize = tarBlockSize
        self.partial = np.full(shape = (tarBlockSize,), fill_value=0.0, dtype=np.float32)
        self.partialLen = 0
        self.isRunning = True

    async def produce(self):
        while self.isRunning:
            await self.consume()

    async def consume(self):
        pdp = await self.source.get_result()
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
    
class AdjustVolume(AbstractWindow):
    def __init__(self, target):
        super().__init__()   
        self.__vol = target

    def inspect(self, pdp):
        if (maxVal := pdp.data.max()) != 0:
            pdp.data = pdp.data * self.__vol / maxVal / 100

class CalcDecibels(AbstractWindow):
    def inspect(self, pdp):
        pdp.meta["dB"] = np.mean(20 * np.log10(np.abs(pdp.data)))

class ApplySquelch(AbstractWindow):
    def __init__(self, squelch):
        super().__init__()
        self.__squelch = squelch
    
    def inspect(self, pdp):
        if self.__squelch >= pdp.meta["dB"]:
            pdp.data = np.zeros(shape=pdp.data.shape)
            pdp.meta["squelched"] = True
        else:
            pdp.meta["squelched"] = False