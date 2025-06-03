

import RPi.GPIO as GPIO
from threading import Thread, Event, Lock
from typing import Any

GPIO.setmode(GPIO.BOARD)

class ButtonHandler():

    def __init__(self, evtQueue):
        self.__events   = {}       # Event tokens to send when an even occurs on a given pin
        self.__regPins  = []       # Registered pins
        self.__evtQ    = evtQueue # Something that implements put and get so we can send events out 
        self.__active  = True

    def register_new_change(self, pin: int, event: Any, timeBtPresses: float = 0.1):
        """
        Set up a button so that it puts event in the event queue when pressed or released

        Parameters
        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        timeBtPresses: float
            Seconds to wait between presses        
        """
        self.__register_new_button(pin, event, GPIO.BOTH, timeBtPresses)

    def register_new_press(self, pin: int, event: Any, timeBtPresses: float = 0.1):
        """
        Set up a button so that it puts event in the event queue when pressed

        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        timeBtPresses: float
            Seconds to wait between presses        
        """
        self.__register_new_button(pin, event, GPIO.FALLING, timeBtPresses)

    def register_new_release(self, pin: int, event: Any, timeBtPresses: float = 0.1):
        """
        Set up a button so that it puts event in the event queue when released

        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        timeBtPresses: float
            Seconds to wait between presses        
        """
        self.__register_new_button(pin, event, GPIO.RISING, timeBtPresses)


    def __register_new_button(self, pin: int, event: Any, sigEdge: int, timeBtPresses: float):
        """
        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        sigEdge: Edge on which to trigger callback
        initDelay: float
            Time to wait between first press and cascading presses
        cascDelay: float
            Time to wait between cascading presses
        """
        print(f"Setting up pin {pin}")
        if pin in self.__regPins:
            raise ValueError(f"Pin {pin} already registerd with this button manager.")

        def btn_change_cb(chan: int):
            """
            Callback to be triggered when button event happens.
            Note:
                runs on a background thread handled by GPIO libs
            """
            self.__evtQ.put(event)

        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            pin,                     # Button that was pressed / released
            sigEdge,                 # Call on down and up
            callback=btn_change_cb,  # Fx that happens when pressed / released
            bouncetime=int(timeBtPresses * 1000) # debounce ms
            )   
        
        # Setup gpio and bookkeeping
        self.__events[pin] = event
        self.__regPins.append(pin)

    def register_new_cascade(self, pin: int, event: Any, initDelay: float = 0.5, cascDelay : float = 0.1):
        """
        Set up a button so that it cascading presses. When pressed the first time,
        sends an event, then if held for the duration specified by initDelay, will
        continually send events every cascDelay seconds until released.

        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        initDelay: float
            Time to wait between first press and cascading presses
        cascDelay: float
            Time to wait between cascading presses
        """
        print(f"Setting up pin {pin}")
        if pin in self.__regPins:
            raise ValueError(f"Pin {pin} already registerd with this button manager.")

        # Shared variables between callback and worker
        sh_sendData = Event() # Way for callback to signal sender thread to start / stop sending

        def btn_sender():
            """
            Worker fx to be run on a thread and handle sending presses 
            """
            
            while self.__active:
                sh_sendData.wait()
                time.sleep(initDelay)
                while sh_sendData.is_set():
                    self.__evtQ.put(event)
                    time.sleep(cascDelay)
            
        def btn_change_cb(chan: int):
            """
            Callback to be triggered when button event happens.
            Note:
                runs on a background thread handled by GPIO libs
            """
            if GPIO.input(chan): # Button up
                sh_sendData.clear()
                print("flag off")
            else: # Button down
                sh_sendData.set()
                print("flag on")
                self.__evtQ.put(event)

        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            pin,                     # Button that was pressed / released
            GPIO.BOTH,               # Call on down and up
            callback=btn_change_cb,  # Fx that happens when pressed / released
            bouncetime=min(50, int(initDelay * 1000))           # debounce ms
            )   
        
        # Setup gpio and bookkeeping
        self.__events[pin] = event
        self.__regPins.append(pin)

        Thread(target=btn_sender, daemon=True).start()

    def cleanup(self):
        GPIO.cleanup()
        self.__active = False



import time
from queue import Queue

def __testing():
    evtQueue = Queue()

    bh = ButtonHandler(evtQueue)

    buttons = [11 , 13 , 15 , 29 , 31 , 33 , 35 , 37]
    events  = ["M3" , "M2" , "M1" , "ok" , "right" , "left" , "down" , "up"]

    for (i , (b, e)) in enumerate(zip(buttons, events)):
        if i in (0,1):
            bh.register_new_cascade(b, e)
        elif i in (2,3):
            bh.register_new_press(b, e)
        elif i in (4,5):
            bh.register_new_release(b, e)
        elif i in (6,7):
            bh.register_new_change(b, e, 0.001)

    print("Registered buttons!!")
    
    try:
        start = time.time()
        ctr = 0
        while True:          # main program continues doing other work
            evt = evtQueue.get()
            ctr += 1
            print(f"[{time.time() - start:06.3f}] > {evt}: {ctr}")
    except KeyboardInterrupt:
        pass
    finally:
        bh.cleanup()

if __name__ == "__main__":
    __testing()


time.monotonic()