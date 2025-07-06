"""
Abstraction of the producer-consumer framework.

This module provides:

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
from pc_model.pc_graph import BaseNode, Graph
import asyncio
class AsyncHandler():
    def __init__(self, mGraph: Graph = None):
        self.mGraph: Graph = mGraph
    
    def run(self):
        """
        Runs the graph that was registered
        """
        # Data verification
        if not self.mGraph:
            raise RuntimeError("Invalid model Configuraiton: no model graph supplied")
        
        if self.mGraph.is_empty():
            raise RuntimeError("Invalid model Configuraiton: no nodes in model graph")
        
        loop = asyncio.get_event_loop()

        # link all nodes according to graph
        for node in self.mGraph:
            for p in node.get_parents():
                node.data.register_source(p.data)

        # obtain coroutines
        coros = [n.data.get_coro() for n in self.mGraph]

        print("About to run")
        loop.run_until_complete(asyncio.gather(*coros))