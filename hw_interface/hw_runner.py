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
import multiprocessing.synchronize
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
        screen  = ScreenDrawer()
        
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
        self.__proc            = None
        self.__btnEvtPairs     = []
        self.__screenDrawInbox = inbox
        self.__params          = params
        self.__btnQueue        = mp.Queue()
        self.__currScreen      = Screens.DEMOD
        
        self.__settingsMenu = Menu("Settings")
        self.__settingsMenu.register_option(MenuOption("Tuning", Screens.FREQTUNE))
        self.__settingsMenu.register_option(MenuOption("Squelch", Screens.SQUELCH))
        self.__settingsMenu.register_option(MenuOption("Volume", Screens.VOLUME))
        self.__settingsMenu.register_option(MenuOption("Demodulation", Screens.DEMOD))
        self.__settingsMenu.register_option(MenuOption("Op5", printaction))
        self.__settingsMenu.register_option(MenuOption("Op6", printaction))

        self.__click_fx_map = {
            Screens.FREQTUNE : self.menu_click_tuning,
            Screens.SQUELCH  : self.menu_click_squelch,
            Screens.DEMOD    : self.menu_click_demod,
        }

        # Fields that we synch between this process and the process that draws to the screen
        self.__latestMeta = {
            "settingsMenu"      : self.__settingsMenu,
            "screen"            : self.__currScreen,
            "FTUNE_cursorPos"   : 5,
            "SQUELCH_cursorPos" : 1,
            "cf"                : params["sdr_cf"].get(),
            "bw"                : params["sdr_dig_bw"].get(),
            "squelch"           : params["sdr_squelch"].get(),
            "vol"               : params["spkr_volume"].get(),
            "timestamp"         : 0,
            "start_time"        : params["start_time"].get(),
            "demod_name"        : params["sdr_decoder"].get_demod_scheme_name(),
        }

    
    # Actions for settings menu:
    def menu_click_tuning(self):
        self.__currScreen = Screens.FREQTUNE
        self.__latestMeta["screen"] = Screens.FREQTUNE
    def menu_click_squelch(self):
        self.__currScreen = Screens.SQUELCH
        self.__latestMeta["screen"] = Screens.SQUELCH
    def menu_click_demod(self):
        self.__currScreen = Screens.DEMOD
        self.__latestMeta["screen"] = Screens.DEMOD

    def handle_event(self, evt):
        if self.__currScreen == Screens.FREQTUNE:
            self.handle_freq_tune(evt)
        elif self.__currScreen == Screens.SETTINGS:
            self.handle_settings(evt)
        elif self.__currScreen == Screens.SQUELCH:
            self.handle_squelch(evt)
        elif self.__currScreen == Screens.DEMOD:
            self.handle_demod(evt)

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
            self.__latestMeta["FTUNE_cursorPos"] = (self.__latestMeta["FTUNE_cursorPos"] - 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.UP)
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__latestMeta["FTUNE_cursorPos"] = (self.__latestMeta["FTUNE_cursorPos"] + 1) % 8
            self.__params["sdr_cf"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)
        
    def handle_squelch(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__params["sdr_squelch"].step(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["squelch"] = self.__params["sdr_squelch"].get()
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__params["sdr_squelch"].step(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["squelch"] = self.__params["sdr_squelch"].get()
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__params["sdr_squelch"].cycle_step_size(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["squelch_step"] = self.__params["sdr_squelch"].get_step_size()
            self.__latestMeta["SQUELCH_cursorPos"] = (self.__latestMeta["SQUELCH_cursorPos"] + 1) % 4
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__params["sdr_squelch"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["squelch_step"] = self.__params["sdr_squelch"].get_step_size()
            self.__latestMeta["SQUELCH_cursorPos"] = (self.__latestMeta["SQUELCH_cursorPos"] - 1) % 4
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        elif evt == hw_enums.BtnEvents.M2:
            self.__currScreen = Screens.FREQTUNE
            self.__latestMeta["screen"] = Screens.FREQTUNE
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)

    def handle_demod(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            pass
        elif evt == hw_enums.BtnEvents.DOWN:
            pass
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__params["sdr_decoder"].cycle_decoding_scheme(step=1) 
            self.__latestMeta["demod_name"] = self.__params["sdr_decoder"].get_demod_scheme_name() 
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__params["sdr_decoder"].cycle_decoding_scheme(step=-1) 
            self.__latestMeta["demod_name"] = self.__params["sdr_decoder"].get_demod_scheme_name() 
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        elif evt == hw_enums.BtnEvents.M2:
            self.__currScreen = Screens.FREQTUNE
            self.__latestMeta["screen"] = Screens.FREQTUNE
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)


    def handle_settings(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__settingsMenu.scroll_up()
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__settingsMenu.scroll_down()
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__click_fx_map[self.__settingsMenu.select()]()
        elif evt == hw_enums.BtnEvents.M2:
            self.__currScreen = Screens.FREQTUNE
            self.__latestMeta["screen"] = Screens.FREQTUNE
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)
        

    def register_btns(self, pairs):
        """
        Iterable of pairs of pin vals and events to send when those vals are pressed
        """
        self.__btnEvtPairs = pairs

    def run_until_sig(self, stopSig : multiprocessing.synchronize.Event):
        HWScreenInterface(self.__screenDrawInbox, self.__btnQueue, self.__latestMeta | {"dB" : 0}, self.__btnEvtPairs, stopSig).start()

        while not stopSig.is_set():
            evt = self.__btnQueue.get()
            print(f"Got event: {evt}")
            self.handle_event(evt)

    def stop(self):
        print("[HWManager] > Stopping")
        self.__proc.join()

    def get_inbox(self):
        return self.__screenDrawInbox