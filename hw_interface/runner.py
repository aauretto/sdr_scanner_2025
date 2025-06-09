"""
Runs all hw brokering on another process
"""

from hw_interface.button_handler import ButtonHandler, PRESS_TYPE
from hw_interface.screen_handler import ScreenDrawer
import multiprocessing as mp
from threading import Thread
from queue import Queue
from enum import Enum, auto
import RPi.GPIO as GPIO
import param_types as ptys
from hw_interface import hw_enums


class HWMenuManager():

    def __init__(self, inbox, params):
        self.__stopSig     = mp.Event()
        self.__proc        = None
        self.__btnEvtPairs = []
        self.__inbox       = inbox
        self.__params      = params
        self.__btnQueue    = mp.Queue()

        self.__currMenu = hw_enums.Menus.FREQTUNE
        self.__menuState = {
            hw_enums.Menus.FREQTUNE : {
                "cursorPos" : 5,
                "cf"        : 88.3,
            },
            hw_enums.Menus.SETTINGS : {
                "otherStuff" : 0,    
            },
        }
        
        self.__latestMeta = {
            **self.__menuState,
            "timestamp" : 0,
            "dB"        : 0,
            "bw"        : 0,
        }

    def __meta_rxer(self):
        while not self.__stopSig.is_set():
            meta = self.__inbox.get()
            if meta:
                for (k, v) in meta.items():
                    self.__latestMeta[k] = v

    def __screen_runner(self, screen: ScreenDrawer):
        screen.run(self.__latestMeta, self.__menuState)

    def __button_runner(self, buttons: ButtonHandler, cfg:list):
        for (p, e, t) in cfg:
            buttons.register_button(p, e, t)
            print(f"[DEBUG] > Registered pin {p} with event {e} and press type {t}")

        print("[DEBUG] > All Buttons registered!")

        buttons.stop_on_signal(self.__stopSig)

    def __worker_process(self):
        buttons = ButtonHandler(self.__btnQueue)
        screen   = ScreenDrawer()
        
        # Meta updater (on hw process handler side) 
        mThread = Thread(target=self.__meta_rxer, args=(), daemon=True, name="thread_meta_updater")

        # Set up buttons on another thread
        bThread = Thread(target=self.__button_runner, args=(buttons, self.__btnEvtPairs), daemon=True, name="thread_button_handler")
        
        # Set up screen handler on annother thread too
        sThread = Thread(target=self.__screen_runner, args=(screen,), daemon=True, name="thread_screen-handler")

        mThread.start()
        bThread.start()
        sThread.start()

        self.__stopSig.wait()
            
        # Shut down gracefully
        screen.stop()
        self.__inbox.put(None)
        sThread.join()
        bThread.join()
        mThread.join()
        GPIO.cleanup()

    def handle_event(self, evt):
        if self.__currMenu == hw_enums.Menus.FREQTUNE:
            self.handle_freq_tune(evt)
        elif self.__currMenu == hw_enums.Menus.SETTINGS:
            self.handle_settings(evt)

    def handle_freq_tune(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__params["sdr_cf"].step(ptys.NumericParam.StepDir.UP) 
            self.__params["sdr"].set_center_freq(self.__params["cf"].get())
            self.__menuState[hw_enums.Menus.FREQTUNE]["cf"] = self.__params["sdr_cf"].get() / 1e6
            print(f"New cf {self.__params['sdr_cf'].get()}")
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__params["sdr_cf"].step(ptys.NumericParam.StepDir.DOWN) 
            self.__params["sdr"].set_center_freq(self.__params["cf"].get())
            self.__menuState[hw_enums.Menus.FREQTUNE]["cf"] = self.__params["sdr_cf"].get() / 1e6
            print(f"New cf {self.__params['sdr_cf'].get()}")
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__menuState[self.__currMenu]["cursorPos"] = (self.__menuState[self.__currMenu]["cursorPos"] - 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.UP)
            
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__menuState[self.__currMenu]["cursorPos"] = (self.__menuState[self.__currMenu]["cursorPos"] + 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            
        elif evt == hw_enums.BtnEvents.OK:
            pass
        elif evt == hw_enums.BtnEvents.M1:
            pass
        elif evt == hw_enums.BtnEvents.M2:
            pass
        elif evt == hw_enums.BtnEvents.M3:
            pass
        self.__inbox.put(self.__menuState)
        

    def register_btns(self, pairs):
        """
        Iterable of pairs of pin vals and events to send when those vals are pressed
        """
        self.__btnEvtPairs = pairs

    def start(self):
        self.__stopSig = mp.Event()

        self.__proc = mp.Process(target=self.__worker_process, args=(), daemon=True)
        self.__proc.start()

        while not self.__stopSig.is_set():
            evt = self.__btnQueue.get()
            print(f"Got event: {evt}")
            self.handle_event(evt)
        



    def stop(self):
        self.__stopSig.set()
        print("[HWManager] > Stopping")
        self.__proc.join()