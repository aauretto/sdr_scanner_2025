"""
Parameters maintained in this module:

For the SDR:
    - Center Freq        => Number
    - Sample Rate        => Number
    - Digital Bandwidth  => Number
    - Squelch            => Number
    - Current chunk size => Number
    
For the Speakers:
    - Current volume     => Number
    - Current chunk size => Number

"""

from threading import Lock
class BaseParam():
    """
    Adds a monitor that will be used when set and get are called
    """
    def __init__(self, startVal):
        self.currVal = startVal
        self.monitor  = Lock()
    def set(self, val):
        with self.monitor:
            self.currVal = val
    def get(self):
        with self.monitor:
            return self.currVal

from enum import IntEnum
class StepDir(IntEnum):
    UP   = 1
    DOWN = -1
class NumericParam(BaseParam):
    def __init__(self, startVal, min, max, stepSize):
        super().__init__(startVal)        
        self.min      = min
        self.max      = max
        self.stepSize = stepSize

    def set(self, val):
        if self.min <= val <= self.max:
            super().set(val)
        
    def step(self, dir : StepDir):
        self.set(self.currVal + self.stepSize * dir)
            
class SysParams():
    """
    Bundles system params and provides a single, threadsafe location in which
    those params can be modified.
    """

    def __init__(self):
        self.__params = {}

    def register_new_param(self, paramKind, name, initialValue, *args):
        """
        Add a new param to this class
        """
        if name in self.__params:
            print(f"System parameter '{name}' already exists. Overwriting.")

        self.__params[name] = paramKind(initialValue, *args)

    def __getitem__(self, key):
        return self.__params[key]

def __testing():
    ps = SysParams()

    ps.register_new_param(BaseParam, "Foo", True)
    ps.register_new_param(NumericParam, "Bar", 0, -1, 10, 1)
    ps.register_new_param(BaseParam, "Foo", 1) # Testing overwrite here... Should get warning
    
    print(f"{ps['Foo'].get() = }")
    ps["Foo"].set(3)
    print(f"{ps['Foo'].get() = }")
    
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(StepDir.UP)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    
if __name__ == "__main__":
    __testing()