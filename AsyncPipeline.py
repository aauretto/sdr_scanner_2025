"""
Async pipeline blocks that can be chained together and run

"""
import asyncio
from abc import ABC, abstractmethod
class AsyncPipeline():
    """
    Basic single-source pipeline that consists of number of stages arranged in
    a linear fashion.
    All stages must inherit from BasePipelineStage

    Notes:
    - Pipeline must be initialized and run in the same thread
    """
    def __init__(self, stages = []):
        self.stages = stages
        self.loop = asyncio.get_event_loop()
    
    def run_pipeline(self):
        """
        Runs the pipeline that was registered
        """
        if not self.stages:
            raise RuntimeError("Invalid Pipeline Configuraiton")

        # link all stages in order
        prevStage, *rest = self.stages
        tasks = [prevStage.execute()]
        for stage in rest:
            print(f"Linking {prevStage}'s outbox to {stage}'s inbox")
            stage.register_prev_stage(prevStage)
            prevStage = stage
            tasks.append(stage.execute())

        self.loop.run_until_complete(asyncio.gather(*tasks))

class BasePipelineStage(ABC):
    """
    Universal base class for all steps in pipeline. Override execute to determine
    behavior for a given stage.
    """
    def __init__(self, prevStage = None):
        self.prevStage = self.register_prev_stage(prevStage)
        self.outbox = asyncio.Queue()

    def register_prev_stage(self, prevStage):
        self.prevStage = prevStage
    
    async def get_result(self):
        return await self.outbox.get()

    @abstractmethod
    async def execute(self):
        pass

class AbstractWorker(BasePipelineStage):
    """
    Inheritable class that has a single predecessor in the pipeline. Ideal for
    steps that transform or modify the data in some way.
    """
    async def execute(self):
        while True:
            data = await self.prevStage.get_result()
            if data is None:
                await self.outbox.put(None)
                break
            await self.outbox.put(self.process(data))

    @abstractmethod
    def process(self, data):
        """
        How to process / transform the data
        """
        pass

class SynchWindow(BasePipelineStage):
    """
    Window stage that will allow synchronous code to provide a queue that fills
    up with the data as it exists at the current point in the pipeline.
    """
    def __init__(self, queue):
        super().__init__()
        self.synchOutbox = queue
    
    async def execute(self):
        while True:
            data = await self.prevStage.get_result()
            self.synchOutbox.put(data)
            if data is None:
                await self.outbox.put(None)
                break
            await self.outbox.put(data)

class Endpoint(BasePipelineStage):
    """
    Endpoint that does not add anything to an outbox (prevents last outbox 
    from becoming massive for long running lines)
    
    Note:
    Technically still has an outbox and will put None there when it is done.
    """
    async def execute(self):
        while True:
            data = await self.prevStage.get_result()
            self.process(data)
            if data is None:
                await self.outbox.put(None)
                break

    def process(self, data):
        pass


def __testing():
    """
    Basic testing and verification
    """

    class Times2(AbstractWorker):
        def process(self, data):
            return 2 * data

    class PrintStage(AbstractWorker):
        def process(self, data):
            print(f"[Print From Pipeline] > {data}")
            return data

    class GenerateInts(BasePipelineStage):
        async def execute(self):
            for x in range(0,10):
                await self.outbox.put(x)
            await self.outbox.put(None)

    pipeline = AsyncPipeline([GenerateInts(), Times2(),Times2(),Times2(), PrintStage(), Endpoint()])
    pipeline.run_pipeline()

if __name__ == "__main__":
    __testing()