

import RPi.GPIO as GPIO
from threading import Thread, Event, Lock
from typing import Any
from enum import Enum, auto

def setup_hw():
    """
    Tell board to use board numbering. Use if not using another module that already sets up GPIO.
    """
    GPIO.setmode(GPIO.BOARD)

class PRESS_TYPE(Enum):
    DOWN    = auto()
    UP      = auto()
    BOTH    = auto()
    CASCADE = auto()

class ButtonHandler():

    def __init__(self, evtQueue):
        self.__events   = {}       # Event tokens to send when an even occurs on a given pin
        self.__regPins  = []       # Registered pins
        self.__active  = True

        self.__evtQ = evtQueue


    def register_button(self, pin: int, event: Any, pressTy: PRESS_TYPE, timeBtPresses: float = 0.1, delayBeforeCasc: float = 0.5):
        """
        Set up a button so that it puts event in the event queue when pressed or released

        Parameters
        ----------
        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        preessTy: PRESS_TYPE
            When an event should be sent
        timeBtPresses: float
            Seconds to wait between presses 
        timeBtCascades: float
            Seconds to wait before rapid-fire presses from button being held down. Must be used with 
            pressTy = PRESS_TYPE.CASCADE to have any effect       
        """
        if pressTy == PRESS_TYPE.DOWN:
            self.__register_new_button(pin, event, GPIO.FALLING, timeBtPresses)
        elif pressTy == PRESS_TYPE.UP:
            self.__register_new_button(pin, event, GPIO.RISING, timeBtPresses)
        elif pressTy == PRESS_TYPE.BOTH:
            self.__register_new_button(pin, event, GPIO.BOTH, timeBtPresses)
        elif pressTy == PRESS_TYPE.CASCADE:
            self.__register_new_cascade(pin, event, delayBeforeCasc, timeBtPresses)



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

    def __register_new_cascade(self, pin: int, event: Any, initDelay: float = 0.5, cascDelay : float = 0.1):
        """
        Set up a button so that it rapid-fire presses when held down. When pressed 
        the first time, sends an event, then if held for the duration specified by
        initDelay, will continually send events every cascDelay seconds until released.

        pin: int
            Pin to attach this listener to
        event: Any
            Object to send on press
        initDelay: float
            Time to wait between first press and cascading presses
        cascDelay: float
            Time to wait between cascading presses
        """
        if pin in self.__regPins:
            raise ValueError(f"Pin {pin} already registerd with this button manager.")

        # Shared variables between callback and worker
        sh_sendData  = Event() # Way for callback to signal sender thread to start / stop sending
        sh_lastPress = time.monotonic()

        def btn_sender():
            """
            Worker fx to be run on a thread and handle sending presses 
            """
            
            while self.__active:
                sh_sendData.wait()
                time.sleep(initDelay)
                
                while not GPIO.input(pin) and (time.monotonic() - sh_lastPress) >= initDelay : # While button is held down
                    self.__evtQ.put(event)
                    time.sleep(cascDelay)
                sh_sendData.clear()
                
            
        def btn_change_cb(chan: int):
            """
            Callback to be triggered when button event happens.
            Note:
                runs on a background thread handled by GPIO libs
            """
            nonlocal sh_lastPress

            sh_lastPress = time.monotonic()
            self.__evtQ.put(event)
            sh_sendData.set()

        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            pin,                     # Button that was pressed / released
            GPIO.FALLING,
            callback=btn_change_cb,  # Fx that happens when pressed / released
            bouncetime=min(50, int(initDelay * 1000))           # debounce ms
            )   
        
        # Setup gpio and bookkeeping
        self.__events[pin] = event
        self.__regPins.append(pin)

        Thread(target=btn_sender, daemon=True).start()

    def __iter__(self):
        """
        Makes class iterable. Will return events as they come if used.
        """
        while self.__active:
            yield self.__evtQ.get()

    def cleanup(self):
        self.__active = False
        self.__evtQ.put(None) # Unstick queue if needed
        GPIO.cleanup()

    def cleanup_on_stop(self, stopSig):
        stopSig.wait()
        self.cleanup()

import multiprocessing as mp
class MPbtnWrapper():
    def __init__(self):
        self.__stopSig     = mp.Event()
        self.__proc        = None
        self.__btnEvtPairs = []
        self.__evtQ        = mp.Queue() 

    def register_btns(self, pairs):
        """
        Iterable of pairs of pin vals and events to send when those vals are pressed
        """
        self.__btnEvtPairs = pairs

    def start(self):
        stopEvt = mp.Event()

        def worker_process(btnCfg, queue, stopSig):
            bh = ButtonHandler(queue)
            
            for (p, e, t) in btnCfg:
                bh.register_button(p, e, t)
                print(f"[Multi-Proc Button Manager] > Registered pin {p} with event {e} and press type {t}!")

            print("[Multi-Proc Button Manager] > All Buttons registered!")
        
            bh.cleanup_on_stop(stopSig) 

        self.__proc = mp.Process(target=worker_process, args=(self.__btnEvtPairs, self.__evtQ, stopEvt), daemon=True)
        self.__proc.start()

        return self.__evtQ

    def get_queue(self):
        return self.__evtQ

    def cleanup(self):
        self.__stopSig.set()
        print("Stopped proc")
        self.__proc.join()


import time

def __testing():
    btnCfg = [
            #    pin    Event     Press
                (11  ,  "M3"    , PRESS_TYPE.DOWN) ,
                (13  ,  "M2"    , PRESS_TYPE.DOWN) ,
                (15  ,  "M1"    , PRESS_TYPE.DOWN) ,
                (29  ,  "ok"    , PRESS_TYPE.DOWN) ,
                (31  ,  "right" , PRESS_TYPE.DOWN) ,
                (33  ,  "left"  , PRESS_TYPE.DOWN) ,
                (35  ,  "down"  , PRESS_TYPE.UP) ,
                (37  ,  "up"    , PRESS_TYPE.CASCADE) ,
             ]

    setup_hw()

    mpManager = MPbtnWrapper()
    mpManager.register_btns(btnCfg)

    evtQ = mpManager.start()


    while (evt := evtQ.get()) != None:
        try:
            print(evt)
        except KeyboardInterrupt:
            mpManager.cleanup()
    
if __name__ == "__main__":
    __testing()


time.monotonic()