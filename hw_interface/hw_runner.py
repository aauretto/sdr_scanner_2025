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
import threading
import RPi.GPIO as GPIO
import param_types as ptys
from hw_interface import hw_enums
from hw_interface.oled_screens import Screens
from hw_interface.oled_menu import Menu, MenuOption

def printaction():
    print("Hello!")    

class HWScreenInterface():
    def __init__(self, inbox, buttonQ, meta, btnPairs):
        """
        TODO explain this stuff
        Manager that runs a process that handles drawing screen and listens to button presses
        """
        self.__screenDrawInbox = inbox
        self.__btnQueue        = buttonQ
        self.__latestMeta      = meta
        self.__btnEvtPairs     = btnPairs

    def __meta_rxer(self):
        """
        Pulls data from inbox and adds it to internal metadata dict
        Note: This function runs in another process and allows us to synchronize
              the state of latestMeta across those processes.
        """
        while (meta := self.__screenDrawInbox.get()) is not None:
            for (k, v) in meta.items():
                self.__latestMeta[k] = v

    def __screen_runner(self, screen: ScreenDrawer):
        screen.run(self.__latestMeta)

    def __button_runner(self, buttons: ButtonHandler, cfg:list, stopSig: threading.Event):
        for (p, e, t) in cfg:
            buttons.register_button(p, e, t)
            print(f"[Buttons] > Registered pin {p} with event {e} and press type {t}")

        print("[Buttons] > All Buttons registered!")

        buttons.stop_on_signal(stopSig)

    def __worker_process(self):
        
        threadStopSig = threading.Event()
        buttons = ButtonHandler(self.__btnQueue)
        screen  = ScreenDrawer()

        # Overwrite signal handler from main process so we can clean up properly when we are told to
        import signal  
        def child_signal_handler(sig, frame):
            print(f"Child proc got signal {sig}")
            threadStopSig.set()
            screen.stop()
        signal.signal(signal.SIGTERM, child_signal_handler) # for SIGTERM (supervisor uses this)
        signal.signal(signal.SIGINT,  child_signal_handler) # for Ctrl+C

        # Meta updater (on hw process handler side) 
        mThread = threading.Thread(target=self.__meta_rxer, args=(), name="thread_meta_updater")

        # Set up buttons on another thread
        bThread = threading.Thread(target=self.__button_runner, args=(buttons, self.__btnEvtPairs, threadStopSig), name="thread_button_handler")
        
        # Set up screen handler on annother thread too
        sThread = threading.Thread(target=self.__screen_runner, args=(screen,), name="thread_screen-handler")

        mThread.start()
        bThread.start()
        sThread.start()

        # Shut down gracefully
        mThread.join()
        sThread.join()
        bThread.join()
        GPIO.cleanup()

    def start(self):
        self.__proc = mp.Process(target=self.__worker_process, args=())
        self.__proc.start()
    
    def stop(self):
        self.__screenDrawInbox.put(None)
        self.__proc.join()


class HWMenuManager():
    def __init__(self, inbox, params):
        self.__screenHandler            = None
        self.__btnEvtPairs     = []
        self.__screenDrawInbox = inbox
        self.__params          = params
        self.__btnQueue        = mp.Queue()
        self.__currScreen      = Screens.FREQTUNE

        self.__settingsMenu = Menu("Settings")
        self.__settingsMenu.register_option(MenuOption("Tuning", Screens.FREQTUNE))
        self.__settingsMenu.register_option(MenuOption("Squelch", Screens.SQUELCH))
        self.__settingsMenu.register_option(MenuOption("Volume", Screens.VOLUME))
        self.__settingsMenu.register_option(MenuOption("Demodulation", Screens.DEMOD))
        self.__settingsMenu.register_option(MenuOption("Bandwitdh", Screens.BANDWIDTH))

        # Fields that we synch between this process and the process that draws to the screen
        self.__latestMeta = {
            "settingsMenu"      : self.__settingsMenu,
            "screen"            : self.__currScreen,
            "FTUNE_cursorPos"   : 5,
            "SQUELCH_cursorPos" : 1,
            "VOL_cursorPos"     : 0,
            "BW_cursorPos"      : 1,
            "cf"                : params["sdr_cf"].get(),
            "bw"                : params["sdr_dig_bw"].get(),
            "squelch"           : params["sdr_squelch"].get(),
            "vol"               : params["spkr_volume"].get(),
            "timestamp"         : 0,
            "start_time"        : params["start_time"].get(),
            "demod_name"        : params["sdr_decoder"].get_demod_scheme_name(),
        }

    
    def register_btns(self, pairs):
        """
        Iterable of pairs of pin vals and events to send when those vals are pressed
        """
        self.__btnEvtPairs = pairs

    def run_until_stop(self):
        """
        Runs until HWMenuManager.stop() is called (Or None is put onto btnQueue somehow but that shouldnt happen)
        """
        # Need to append dB starting value here since its displayed in two screens
        self.__screenHandler = HWScreenInterface(self.__screenDrawInbox, self.__btnQueue, self.__latestMeta | {"dB" : 0}, self.__btnEvtPairs)
        self.__screenHandler.start()

        while (evt := self.__btnQueue.get()) is not None:
            print(f"Got event: {evt}")
            self.handle_event(evt)

    def stop(self):
        self.__btnQueue.put(None)
        self.__screenHandler.stop()

    def get_inbox(self):
        return self.__screenDrawInbox

    def set_current_screen(self, screen):
        self.__currScreen = screen
        self.__latestMeta["screen"] = screen

    def handle_event(self, evt):
        """
        Send received event to proper handler based on screen
        """
        if self.__currScreen == Screens.FREQTUNE:
            self.handle_freq_tune(evt)
        elif self.__currScreen == Screens.SETTINGS:
            self.handle_settings(evt)
        elif self.__currScreen == Screens.SQUELCH:
            self.handle_squelch(evt)
        elif self.__currScreen == Screens.VOLUME:
            self.handle_vol(evt)
        elif self.__currScreen == Screens.DEMOD:
            self.handle_demod(evt)
        elif self.__currScreen == Screens.BANDWIDTH:
            self.handle_bw(evt)

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
            self.__latestMeta["SQUELCH_cursorPos"] = (self.__latestMeta["SQUELCH_cursorPos"] + 1) % 4
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__params["sdr_squelch"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["SQUELCH_cursorPos"] = (self.__latestMeta["SQUELCH_cursorPos"] - 1) % 4
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)

    def handle_bw(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__params["sdr_dig_bw"].step(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["bw"] = self.__params["sdr_dig_bw"].get()
            # Update filter params to new BW
            n,d = self.__params["sdr_decoder"].create_filter(self.__latestMeta["bw"], self.__params["sdr_fs"])
            self.__params["sdr_lp_num"].set(n)
            self.__params["sdr_lp_denom"].set(d)
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__params["sdr_dig_bw"].step(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["bw"] = self.__params["sdr_dig_bw"].get()
            # Update filter params to new BW
            n,d = self.__params["sdr_decoder"].create_filter(self.__latestMeta["bw"], self.__params["sdr_fs"])
            self.__params["sdr_lp_num"].set(n)
            self.__params["sdr_lp_denom"].set(d)
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__params["sdr_dig_bw"].cycle_step_size(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["BW_cursorPos"] = (self.__latestMeta["BW_cursorPos"] + 1) % 5
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__params["sdr_dig_bw"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["BW_cursorPos"] = (self.__latestMeta["BW_cursorPos"] - 1) % 5
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)

    def handle_vol(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__params["spkr_volume"].step(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["vol"] = self.__params["spkr_volume"].get()
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__params["spkr_volume"].step(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["vol"] = self.__params["spkr_volume"].get()
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.__params["spkr_volume"].cycle_step_size(ptys.NumericParam.StepDir.UP)
            self.__latestMeta["VOL_cursorPos"] = (self.__latestMeta["VOL_cursorPos"] + 1) % 2
        elif evt == hw_enums.BtnEvents.LEFT:
            self.__params["spkr_volume"].cycle_step_size(ptys.NumericParam.StepDir.DOWN)
            self.__latestMeta["VOL_cursorPos"] = (self.__latestMeta["VOL_cursorPos"] - 1) % 2
        elif evt == hw_enums.BtnEvents.M1:
            self.__currScreen = Screens.SETTINGS
            self.__latestMeta["screen"] = Screens.SETTINGS
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
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)


    def handle_settings(self, evt):
        if evt == hw_enums.BtnEvents.UP:
            self.__settingsMenu.scroll_up()
        elif evt == hw_enums.BtnEvents.DOWN:
            self.__settingsMenu.scroll_down()
        elif evt == hw_enums.BtnEvents.RIGHT:
            self.set_current_screen(self.__settingsMenu.select())
        # Send updated state of system params over to screen drawer
        self.__screenDrawInbox.put(self.__latestMeta)
        