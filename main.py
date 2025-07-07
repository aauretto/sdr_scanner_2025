

import system_params as sps
import asyncio

import time

from speaker_manager import SpeakerManager
from rtlsdr import RtlSdr
from queue import Queue
from threading import Thread
import param_types as ptys

def main():
    """
    Main entrypoint for program
    """
    # initialize stuff
    params = init_params()
    setup_sdr(params)
    hwManager, stopSig = start_gpio_hw(params)

    # Connect decoding pipeline to speakers
    bridgeToSpeakers = Queue()
    bridgeToHW       = hwManager.get_inbox()
    pipelineThread   = Thread(target=pipeline_worker, args = (bridgeToSpeakers, bridgeToHW, params), daemon=True)

    sm = SpeakerManager(blockSize=params["spkr_chunk_sz"], sampRate=params["spkr_fs"])
    sm.set_source(bridgeToSpeakers)
    sm.init_stream()
    sm.start()

    pipelineThread.start() # Will go forever unless error encountered.

    # Clean up
    pipelineThread.join()
    stopSig.set()
    hwManager.stop()
    sm.stop()

from hw_interface import BtnEvents, PRESS_TYPE, HWMenuManager
import multiprocessing as mp
def start_gpio_hw(params):
    btnCfg = [
        #    pin    Event             Press Type
            (17  ,  BtnEvents.M3    , PRESS_TYPE.DOWN) ,
            (27  ,  BtnEvents.M2    , PRESS_TYPE.DOWN) ,
            (22  ,  BtnEvents.M1    , PRESS_TYPE.DOWN) ,
            (5   ,  BtnEvents.OK    , PRESS_TYPE.DOWN) ,
            (6   ,  BtnEvents.RIGHT , PRESS_TYPE.CASCADE) ,
            (13  ,  BtnEvents.LEFT  , PRESS_TYPE.CASCADE) ,
            (19  ,  BtnEvents.DOWN  , PRESS_TYPE.CASCADE) ,
            (26  ,  BtnEvents.UP    , PRESS_TYPE.CASCADE) ,
            ]

    bridgeToHW = mp.Queue() # Gets meta from pipeline over to screen
    hwManager  = HWMenuManager(bridgeToHW, params)
    stopSig    = mp.Event()

    def hw_worker():
        hwManager.register_btns(btnCfg)
        hwManager.run_until_sig(stopSig)
    Thread(target=hw_worker, args=(), daemon=True).start()
    
    return hwManager, stopSig
    
def init_params():
    """
    Set up initial parameters for the scanner
    """
    from demodulation import DemodulationManager as DMgr
    params = sps.SysParams()


    # =========================================================================================================================== #
    #                          Type of param      Name                InitVal    Min      Max    StepSizes                        #
    # =========================================================================================================================== #
    params.register_new_param(ptys.NumericParam , "sdr_cf"        ,    88.3e6 , 30e6 , 1766e6 , [1e4,1e5,1e6,1e7,1e8,1e9,1e2,1e3] )
    params.register_new_param(ptys.NumericParam , "sdr_fs"        ,    0.25e6 ,    0 ,    2e9 ,  None                             )
    params.register_new_param(ptys.NumericParam , "sdr_dig_bw"    ,     150e3 ,  1e3 ,  250e3 , [10e3,100e3,1e3]                  )
    params.register_new_param(ptys.ObjParam     , "sdr_decoder"   ,    DMgr() ,                                                   )
    params.register_new_param(ptys.NumericParam , "sdr_squelch"   ,       -20 ,  -40 ,      2 , [1, 0.1, 0.01, 10]                )
    params.register_new_param(ptys.NumericParam , "sdr_chunk_sz"  ,     2**14 ,    1 ,   None , [1]                               )
    params.register_new_param(ptys.NumericParam , "spkr_volume"   ,       0.5 ,    0 ,    100 , [10,1]                            )
    params.register_new_param(ptys.NumericParam , "spkr_chunk_sz" ,     2**12 ,    1 ,   None , [1]                               )
    params.register_new_param(ptys.NumericParam , "spkr_fs"       ,     44100 ,    1 ,   None , [1]                               )
    params.register_new_param(ptys.ObjParam     , "start_time"    , time.time(),                                                  )

    num, denom = params["sdr_decoder"].create_filter(params["sdr_dig_bw"], params["sdr_fs"])
    params.register_new_param(ptys.ObjParam, "sdr_lp_num", num)
    params.register_new_param(ptys.ObjParam, "sdr_lp_denom", denom)


    return params

def setup_sdr(params):
    sdr = RtlSdr()

    # Configure SDR
    sdr.center_freq = params["sdr_cf"].get()
    sdr.sample_rate = params["sdr_fs"].get()
    sdr.freq_correction = 60
    sdr.gain = 'auto'

    params["sdr_cf"].set(sdr.get_center_freq())
    params.register_new_param(ptys.ObjParam, "sdr", sdr)
    return sdr

def pipeline_worker(toSpeakers, toHW, params):
    # Create loop for this thread
    from pc_model import AsyncHandler, Graph as PCgraph
    from system_pipeline_stages import ProvideRawRF, Filter, Downsample, RechunkArray, ReshapeArray, Endpoint, DemodulateRF, CalcDecibels, ApplySquelch, AdjustVolume, Endpoint
    from pc_model               import FxApplyWindow
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Set up and launch decoding / playback pipeline

    m = PCgraph()
    m.add_linear_chain([ProvideRawRF(params["sdr"], params["sdr_chunk_sz"]),
                        CalcDecibels(),
                        ApplySquelch(params["sdr_squelch"]),
                        DemodulateRF(params["sdr_decoder"]),
                        Filter(params["sdr_lp_num"], params["sdr_lp_denom"]),
                        Downsample(params["sdr_fs"], params["spkr_fs"]),
                        RechunkArray(params["spkr_chunk_sz"]),
                        AdjustVolume(params["spkr_volume"]),
               
                        # Data is now audio ready for speakers
                        ReshapeArray((-1,1)),
                        FxApplyWindow(lambda d : toSpeakers.put(d.data)),
                        FxApplyWindow(lambda d : toHW.put(d.meta)),
                        Endpoint()])
    
    pipeline = AsyncHandler(m)
    pipeline.run()

    loop.close()

if __name__ == "__main__":
    main()