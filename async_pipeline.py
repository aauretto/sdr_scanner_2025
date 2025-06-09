"""
Async pipeline blocks that can be chained together and run.

This module provides:
- An AsyncPipeline implementation that coordinates data flow between stages of the pipeline.
- A number of pipeline stages that are used to do work on some stream of data.

Notes on naming
---------------
The pipeline stages this module provides are named according to the following convention:
- Worker = Stage that modifies incoming data and sends that modified data down the pipeline. 
           These classes modify data through their process() method.
- Window = Stage that does not modify incoming data and instead allows the data to pass through 
           unchanged (but may do some other computation such as print important information).
           These classes examine data through their inspect() method.

Notes on stage behavior
-----------------------
The stages in this class (other than BaseStage) assume None to be a sentinel value and will stop running when they encounter it.

"""

_CURR_GID = 0
def _GET_GID():
    global _CURR_GID
    _CURR_GID += 1
    return _CURR_GID

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


# =========================================================================== #
#                           Pipeline Stage Classes
# =========================================================================== #
# Some classes that can be used and provide some basic pipeline stage 
# functionality. 

class BasePipelineStage(ABC):
    """
    Universal base class for all steps in pipeline. Override execute to determine
    behavior for a given stage.
    """
    def __init__(self, prevStage = None):
        self.prevStage = self.register_prev_stage(prevStage)
        self.outbox = asyncio.Queue()
        self.gid = _GET_GID()

    def register_prev_stage(self, prevStage):
        self.prevStage = prevStage
    
    async def get_result(self):
        return await self.outbox.get()

    @abstractmethod
    async def execute(self):
        pass

import time

class AbstractWorker(BasePipelineStage):
    """
    Inheritable class that has a single predecessor in the pipeline. Ideal for
    steps that transform or modify the data in some way.
    Note:
    - If process returns not None, future pipeline stages may shut down 
    """
    async def execute(self):
        while True:
            start = time.time()
            data = await self.prevStage.get_result()
            if data is None:
                await self.outbox.put(None)
                break
            await self.outbox.put(self.process(data))
            # print(f"{self.__class__.__name__}")
            # t = data.meta["timestamp"]
            # time_str = time.strftime("%H:%M:%S", time.localtime(t))
            # ms = int((t % 1) * 1000)
            # print(f"[{self.gid}][{time_str}.{ms:03d}] > {self.__class__.__name__} > {time.time() - start} to process")

    @abstractmethod
    def process(self, data):
        """
        How to process / transform the data
        """
        pass

class AbstractWindow(BasePipelineStage):
    """
    Inheritable class that has a single predecessor in the pipeline. Does not 
    modify data but provides it via process for inspection.
    """
    async def execute(self):
        while True:
            start = time.time()
            data = await self.prevStage.get_result()
            self.inspect(data)
            if data is None:
                await self.outbox.put(None)
                break
            await self.outbox.put(data)
            # t = data.meta["timestamp"]
            # time_str = time.strftime("%H:%M:%S", time.localtime(t))
            # ms = int((t % 1) * 1000)
            # print(f"[{self.gid}][{time_str}.{ms:03d}] > {self.__class__.__name__} > {time.time() - start} to process")




    @abstractmethod
    def inspect(self, data):
        """
        How to inspect data
        """
        pass

class FxApplyWorker(AbstractWorker):
    """
    Worker that takes a function and applies it to data. Allows use of the 
    AbstractWorker class but without inheriting if the if the desired work is 
    a simple transform or something.
    Note:
    - The function passed in should return a non-None value otherwise it will 
      shut down later pipeline stages. For function application without  
    """
    def __init__(self, fx):
        super().__init__()
        self.__fx = fx
    def process(self, data):
        return self.__fx(data)

class FxApplyWindow(AbstractWindow):
    """
    Window that takes a function and applies it on data. Allows use of the 
    AbstractWindow class but without inheriting if the if the desired work is 
    simple.
    """
    def __init__(self, fx):
        super().__init__()
        self.__fx = fx
    def inspect(self, data):
        self.__fx(data)

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

    class PrintStage(AbstractWindow):
        def inspect(self, data):
            print(f"[Print From Pipeline] > {data}")

    class GenerateInts(BasePipelineStage):
        async def execute(self):
            for x in range(0,10):
                await self.outbox.put(x)
            await self.outbox.put(None)

    pipeline = AsyncPipeline([GenerateInts(), Times2(),Times2(),Times2(), PrintStage(), Endpoint()])
    pipeline.run_pipeline()

if __name__ == "__main__":
    __testing()