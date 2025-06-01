from async_pipeline import BasePipelineStage, AbstractWorker
import numpy as np

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

class Volume(AbstractWorker):
    """
    TODO: figure out exactly how volume control should behave
    """
    def __init__(self, ref):
        pass