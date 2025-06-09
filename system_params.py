"""
Maintains single location for system parameters as monitored objects.
See params for different param types.
"""

from threading import Lock
class SysParams():
    """
    Bundles system params and provides a single, threadsafe location in which
    those params can be modified.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """
        Overriden new to enforce singleton class
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Avoid TOCVTOU Bug
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__params = {}

    def register_new_param(self, paramKind, name, initialValue, *args):
        """
        Add a new param to this class
        """
        if name in self.__params:
            print(f"System parameter '{name}' already exists. Overwriting.")
        print(f"[System Params] > Registering parameter under key {name}")
        self.__params[name] = paramKind(initialValue, *args)

    def __getitem__(self, key):
        return self.__params[key]

def __testing():
    from param_types import BaseParam, NumericParam

    ps = SysParams()

    ps.register_new_param(BaseParam, "Foo", True)
    ps.register_new_param(NumericParam, "Bar", 0, -1, 10, 1)
    ps.register_new_param(BaseParam, "Foo", 1) # Testing overwrite here... Should get warning
    
    print(f"{ps['Foo'].get() = }")
    ps["Foo"].set(3)
    print(f"{ps['Foo'].get() = }")
    
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(NumericParam.StepDir.UP)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(NumericParam.StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(NumericParam.StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    ps["Bar"].step(NumericParam.StepDir.DOWN)
    print(f"{ps['Bar'].get() = }")
    
if __name__ == "__main__":
    __testing()