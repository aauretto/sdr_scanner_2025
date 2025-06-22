"""
File containing classes that manage hardware.

Two classes are in this file:
- HWScreenInterface
    A wrapper that launches a process responsible for managing the screen and listening for button presses.
    Actual drawing logic found in screen_handler.py
- HWMenuManager
    A wrapper that will listen to the button events sent by HWScreenInterface and alter state according to
    those presses. 
"""

from hw_interface.button_handler import ButtonHandler
from hw_interface.screen_handler import ScreenDrawer
import multiprocessing as mp
from threading import Thread
import RPi.GPIO as GPIO
import param_types as ptys
from hw_interface import hw_enums
from hw_interface.oled_screens import Screens
from hw_interface.oled_menu import Menu, MenuOption

def printaction():
    print("Hello!")    

class HWScreenInterface():
    def __init__(self, inbox, buttonQ, meta, btnPairs, stopSig):
        """
        TODO explain this stuff
        Manager that runs a process that handles drawing screen and listens to button presses
        """
        self.__screenDrawInbox = inbox
        self.__btnQueue        = buttonQ
        self.__latestMeta      = meta
        self.__stopSig         = stopSig
        self.__btnEvtPairs     = btnPairs

    def __meta_rxer(self):
        """
        Pulls data from inbox and adds it to internal metadata dict
        Note: This function runs in another process and allows us to synchronize
              the state of latestMeta across those processes.
        """
        while not self.__stopSig.is_set():
            meta = self.__screenDrawInbox.get()
            if meta:
                for (k, v) in meta.items():
                    self.__latestMeta[k] = v

    def __screen_runner(self, screen: ScreenDrawer):
        screen.run(self.__latestMeta)

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
        self.__screenDrawInbox.put(None)
        sThread.join()
        bThread.join()
        mThread.join()
        GPIO.cleanup()

    def start(self):

        self.__proc = mp.Process(target=self.__worker_process, args=(), daemon=True)
        self.__proc.start()



class HWMenuManager():
    def __init__(self, inbox, params):
        self.__stopSig         = mp.Event()
        self.__proc            = None
        self.__btnEvtPairs     = []
        self.__screenDrawInbox = inbox
        self.__params          = params
        self.__btnQueue        = mp.Queue()
        self.__currScreen      = Screens.FREQTUNE
        
        self.__settingsMenu = Menu("Settings")
        self.__settingsMenu.register_option(MenuOption("Op1", printaction))
        self.__settingsMenu.register_option(MenuOption("Op2", printaction))
        self.__settingsMenu.register_option(MenuOption("Op3", printaction))
        self.__settingsMenu.register_option(MenuOption("Op4", printaction))
        self.__settingsMenu.register_option(MenuOption("Op5", printaction))
        self.__settingsMenu.register_option(MenuOption("Op6", printaction))

        # Fields that we synch between this process and the process that draws to the screen
        self.__latestMeta = {
            "settingsMenu"    : self.__settingsMenu,
            "screen"          : self.__currScreen,
            "FTUNE_cursorPos" : 5,
            "cf"              : params["sdr_cf"].get(),
            "bw"              : params["sdr_dig_bw"].get(),
            "squelch"         : params["sdr_squelch"].get(),
            "vol"             : params["spkr_volume"].get(),
            "timestamp"       : 0,
            "dB"              : 0,
        }

    
    def handle_event(self, evt):
        if self.__currScreen == Screens.FREQTUNE:
            self.handle_freq_tune(evt)
        elif self.__currScreen == Screens.SETTINGS:
            self.handle_settings(evt)

    def handle_freq_tune(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__params["sdr_cf"].step(ptys.NumericParam.StepDir.UP) 
            self.__params["sdr"].set_center_freq(self.__params["sdr_cf"].get())
            self.__latestMeta["cf"] = self.__params["sdr_cf"].get()
            print(f"New cf {self.__params['sdr_cf'].get()}")
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__params["sdr_cf"].step(ptys.NumericParam.StepDir.DOWN) 
            self.__params["sdr"].set_center_freq(self.__params["sdr_cf"].get())
            self.__latestMeta["cf"] = self.__params["sdr_cf"].get()
            print(f"New cf {self.__params['sdr_cf'].get()}")
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__latestMeta["cursorPos"] = (self.__latestMeta["cursorPos"] - 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.UP)
            
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__latestMeta["cursorPos"] = (self.__latestMeta["cursorPos"] + 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            
        elif evt == hw_enums.BtnEvents.OK:
            pass
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        elif evt == hw_enums.BtnEvents.M2:
            pass
        elif evt == hw_enums.BtnEvents.M3:
            pass
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)
        
    def handle_settings(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__settingsMenu.scroll_up()
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__settingsMenu.scroll_down()
        elif evt == hw_enums.BtnEvents.LEFT:
            pass
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__settingsMenu.select()()
        elif evt == hw_enums.BtnEvents.OK:
            pass
        elif evt == hw_enums.BtnEvents.M1:
            pass
        elif evt == hw_enums.BtnEvents.M2:
            self.__currScreen = Screens.FREQTUNE
            self.__latestMeta["screen"] = Screens.FREQTUNE
        elif evt == hw_enums.BtnEvents.M3:
            pass
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)
        

    def register_btns(self, pairs):
        """
        Iterable of pairs of pin vals and events to send when those vals are pressed
        """
        self.__btnEvtPairs = pairs

    def start(self):
        self.__stopSig = mp.Event()

        HWScreenInterface(self.__screenDrawInbox, self.__btnQueue, self.__latestMeta, self.__btnEvtPairs, self.__stopSig).start()

        while not self.__stopSig.is_set():
            evt = self.__btnQueue.get()
            print(f"Got event: {evt}")
            self.handle_event(evt)

    def stop(self):
        self.__stopSig.set()
        print("[HWManager] > Stopping")
        self.__proc.join()

    def get_inbox(self):
        return self.__screenDrawInbox