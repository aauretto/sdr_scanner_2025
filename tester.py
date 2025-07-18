
from hw_interface import HWMenuManager, PRESS_TYPE, Menus, BtnEvents
import time
import multiprocessing as mp



def __testing():
    from main import init_params
    btnCfg = [
            #    pin    Event                                  Press Type
                (17  ,  BtnEvents.M3    , PRESS_TYPE.DOWN) ,
                (27  ,  BtnEvents.M2    , PRESS_TYPE.DOWN) ,
                (22  ,  BtnEvents.M1    , PRESS_TYPE.DOWN) ,
                (5   ,  BtnEvents.OK    , PRESS_TYPE.DOWN) ,
                (6   ,  BtnEvents.RIGHT , PRESS_TYPE.DOWN) ,
                (13  ,  BtnEvents.LEFT  , PRESS_TYPE.DOWN) ,
                (19  ,  BtnEvents.DOWN  , PRESS_TYPE.UP) ,
                (26  ,  BtnEvents.UP    , PRESS_TYPE.CASCADE) ,
             ]

    bridgeToHW = mp.Queue() # Gets meta from pipeline over to screen
    hwManager =  HWMenuManager(bridgeToHW, init_params())
    def hw_worker():
        hwManager.register_btns(btnCfg)
        hwManager.start()
            
if __name__ == "__main__":
    __testing()