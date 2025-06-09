

import RPi.GPIO as GPIO
from threading import Thread, Event, Lock
from typing import Any
from enum import Enum, auto

class PRESS_TYPE(Enum):
    DOWN    = auto()
    UP      = auto()
    BOTH    = auto()
    CASCADE = auto()

import time
class ButtonHandler():

    def __init__(self, evtQueue):
        self.__events   = {}       # Event tokens to send when an even occurs on a given pin
        self.__regPins  = []       # Registered pins
        self.__active  = True

        self.__evtQ = evtQueue
        GPIO.setmode(GPIO.BCM)   
    

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

    def stop(self):
        self.__active = False
        print("[Button Manager] > Stopping")
        self.__evtQ.put(None) # Unstick queue if needed

    def stop_on_signal(self, stopSig):
        stopSig.wait()
        self.stop()


