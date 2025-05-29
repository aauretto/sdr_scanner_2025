"""
Async pipeline blocks that can be chained together and run

"""
import asyncio
from abc import ABC, abstractmethod

class AsyncPipeline():
    """
    Basic single-source pipeline that consists of (somewhat restrictively) a
    source and any number of stages.
    Source must be an object that provides a .generate() coroutine
    Stages must be a list of objects that inherit from BasePipelineStage
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

class TransformStage(BasePipelineStage):
    """
    Inheritable class that has a single predecessor in the pipeline
    """
    async def execute(self):
        while True:
            data = await self.prevStage.get_result()
            if data is None:
                await self.outbox.put(None)
                break
            await self.outbox.put(self.transform(data))

    @abstractmethod
    def transform(self, data):
        pass

def main():
    """
    Basic testing and verification
    """
    class Times2(TransformStage):
        def transform(self, data):
            return 2 * data

    class PrintStage(TransformStage):
        def transform(self, data):
            print(f"[Print From Pipeline] > {data}")
            return data

    class GenerateInts(BasePipelineStage):
        async def execute(self):
            for x in range(0,10):
                await self.outbox.put(x)
            await self.outbox.put(None)

    pipeline = AsyncPipeline([GenerateInts(), Times2(),Times2(),Times2(), PrintStage()])
    pipeline.run_pipeline()

if __name__ == "__main__":
    main()