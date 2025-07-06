# =========================================================================== #
#                              Consumer Classes
# =========================================================================== #
# Some classes that can be used with the runner in pc_runner to assemble a 
# producer-consumer network

from abc import ABC, abstractmethod
import asyncio

class BaseProducer(ABC):
    """
    Single output producer base class
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.outbox = asyncio.Queue()
        self.__num_consumers = 0
    
    def add_consumer(self):
        self.__num_consumers += 1

    async def get_result(self):
        return await self.outbox.get()

    async def stop(self):
        for n in range(self.__num_consumers):
            await self.outbox.put(None) 

    def get_coro(self):
        return self.produce()

    @abstractmethod
    async def produce(self):
        pass

class BaseConsumer(ABC):
    """
    Single source consumer base class
    """
    def __init__(self, source=None, **kwargs):
        super().__init__()
        if source:
            self.register_source(source)

    def register_source(self, source):
        if not isinstance(source, BaseProducer):
            raise TypeError(f"Expected BaseProducer, got {type(source).__name__}")
        self.source = source
        source.add_consumer()
    
    def get_coro(self):
        return self.consume()

    @abstractmethod
    async def consume(self):
        pass

class AbstractWorker(BaseProducer, BaseConsumer):
    """
    Inheritable class that has a single predecessor in the pipeline. Ideal for
    steps that transform or modify the data in some way.
    Note:
    - If process returns not None, future pipeline stages may shut down 
    """
    def __init__(self, source=None):
        super().__init__(source=source)

    async def consume(self):
        return await self.source.get_result()
    
    async def produce(self):
        while (data := await self.consume()) is not None:
            await self.outbox.put(self.process(data))
        await self.stop()


    @abstractmethod
    def process(self, data):
        """
        How to process / transform the data
        """
        pass

class AbstractWindow(BaseProducer, BaseConsumer):
    """
    Inheritable class that has a single predecessor in the pipeline. Does not 
    modify data but provides it via process for inspection.
    """
    def __init__(self, source=None):
        super().__init__(source=source)

    async def consume(self):
        return await self.source.get_result()
    
    async def produce(self):
        while (data := await self.consume()) is not None:
            self.inspect(data)
            await self.outbox.put(data)
        await self.stop()

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
      shut down later nodes. 
    """
    def __init__(self, fx):
        super().__init__(source=None)
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
        super().__init__(source=None)
        self.__fx = fx
    def inspect(self, data):
        self.__fx(data)

def __testing():
    """
    Basic testing and verification
    """

if __name__ == "__main__":
    __testing()