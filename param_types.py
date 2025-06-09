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
        return self.currVal
    
from enum import IntEnum
class NumericParam(BaseParam):
    class StepDir(IntEnum):
        UP   = 1
        DOWN = -1
    def __init__(self, startVal, min, max, stepSizes):
        super().__init__(startVal)        
        self.min      = min
        self.max      = max
        self.stepSizes = stepSizes
        self.stepSizeIdx = 0

    def get_step_size(self):
        return self.stepSizes[self.stepSizeIdx]
    
    def cycle_step_size(self, dir : StepDir):
        self.stepSizeIdx = (self.stepSizeIdx + dir) % len(self.stepSizes)

    def step(self, dir : StepDir):
        self.set(self.currVal + self.get_step_size() * dir)

    def set(self, val):
        if val <= self.min:
            super().set(self.min)
        elif val >= self.max:
            super().set(self.max)
        else:
            super().set(val)

    def __int__(self):
        with self.monitor:
            return int(self.currVal)
    def __float__(self):
        with self.monitor:
            return float(self.currVal)
    def __repr__(self):
        return f"NumericParam({self.get()})"
    def __index__(self):
        return self.get()

    def __add__(self, other):
        return self.get() + other
    def __radd__(self, other):
        return self.get() + other
    def __sub__(self, other):
        return self.get() - other
    def __rsub__(self, other):
        return other - self.get()
    def __mul__(self, other):
        return self.get() * other
    def __rmul__(self, other):
        return other * self.get()
    def __truediv__(self, other):
        return self.get() / other
    def __rtruediv__(self, other):
        return other / self.get()
    def __floordiv__(self, other):
        return self.get() // other
    def __rfloordiv__(self, other):
        return other // self.get()
    def __mod__(self, other):
        return self.get() % other
    def __rmod__(self, other):
        return other % self.get()
    
    def __eq__(self, other):
        return self.get() == other
    def __ne__(self, other):
        return not self.__eq__(other)
    def __le__(self, other):
        return self.get() <= other
    def __ge__(self, other):
        return self.get() >= other
    def __gt__(self, other):
        return self.get() > other
    def __lt__(self, other):
        return self.get() < other
    
class FuncParam(BaseParam):
    def __call__(self, *args, **kwargs):
        return self.get()(*args, **kwargs)

class ObjParam(BaseParam):
    def __getattr__(self, name):
        """
        Forward any attribute access thats not in this class (get,set,etc)
        Note this means that we can't properly encapsulate objects that have those
        methods.
        """
        attr = getattr(self.currVal, name)

        if callable(attr):
            # If it's a method, wrap it to acquire the lock
            def locked_method(*args, **kwargs):
                with self.monitor:
                    return attr(*args, **kwargs)
            return locked_method
        else:
            # Attribute access (e.g., shape, dtype)
            with self.monitor:
                return attr



def __testing():
    import numpy as np

    p = BaseParam(2)
    print(p.get())
    p.set(0)
    print(p.get())

    print("========================================")
    
    p = NumericParam(1, 0, 2, [0.5])
    
    print(p + 1)
    print(p - 2)
    print(2 - p)
    print(p / 2)
    print(2 / p)
    print(p % 2)
    print(2 % p)

    p.step(NumericParam.StepDir.UP)
    print(p.get())
    p.step(NumericParam.StepDir.UP)
    print(p.get())
    p.step(NumericParam.StepDir.UP)
    print(p.get())

    print("========================================")

    p = FuncParam(lambda x : x)

    print(p(0))
    p.set(lambda x : x + 1)
    print(p(0))

    print("========================================")

    a = np.array([0,1,2,3,4])

    p = ObjParam(a)

    print(p.get())
    print(p.min())
    p.set(np.array([1,2,3,4,5]))
    print(p.min())


if __name__ == "__main__":
    __testing()