

import system_params as sps
import asyncio

from speaker_manager import SpeakerManager
from rtlsdr import RtlSdr
from queue import Queue
from threading import Thread
from async_pipeline import AsyncPipeline
import param_types as ptys

def main():
    """
    Main entrypoint for program
    """
    # initialize stuff
    params = init_params()
    setup_sdr(params)
    setup_lowpass(params)
    hwManager = start_gpio_hw(params)

    # Connect decoding pipeline to speakers
    bridgeFromPipeline = Queue()
    pipelineThread = Thread(target=pipeline_worker, args = (bridgeFromPipeline, params), daemon=True)

    sm = SpeakerManager(blockSize=params["spkr_chunk_sz"], sampRate=params["spkr_fs"])
    sm.set_source(bridgeFromPipeline)
    sm.init_stream()
    sm.start()

    pipelineThread.start() # Will go forever unless error encountered.
    pipelineThread.join()
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
            (6   ,  BtnEvents.RIGHT , PRESS_TYPE.DOWN) ,
            (13  ,  BtnEvents.LEFT  , PRESS_TYPE.DOWN) ,
            (19  ,  BtnEvents.DOWN  , PRESS_TYPE.CASCADE) ,
            (26  ,  BtnEvents.UP    , PRESS_TYPE.CASCADE) ,
            ]

    bridgeToHW = mp.Queue() # Gets meta from pipeline over to screen
    hwManager =  HWMenuManager(bridgeToHW, params)
    def hw_worker():
        hwManager.register_btns(btnCfg)
        hwManager.start()
    Thread(target=hw_worker, args=(), daemon=True).start()
    return hwManager
    
def init_params():
    """
    Set up initial parameters for the scanner
    """
    from demodulation import DECODE_FM

    params = sps.SysParams()

    # ========================================================================================================================== #
    #                          Type of param      Name              InitVal    Min      Max      StepSizes                       #
    # ========================================================================================================================== #
    params.register_new_param(ptys.NumericParam , "sdr_cf"        ,    88.3e6 , 30e6 , 1766e6 ,    [1e4,1e5,1e6,1e7,1e8,1e9,1e2,1e3]  )
    params.register_new_param(ptys.NumericParam , "sdr_fs"        ,    0.25e6 ,    0 ,    2e9 ,     None                          )
    params.register_new_param(ptys.NumericParam , "sdr_dig_bw"    ,     150e3 ,  1e3 ,  250e3 ,    [10e3,100e3,1e3]               )
    params.register_new_param(ptys.FuncParam    , "sdr_dec_fx"    , DECODE_FM ,                                                   )
    params.register_new_param(ptys.NumericParam , "sdr_squelch"   ,       -20 ,  -40 ,      1 ,    [10, 0.001, 0.1, 1]            )
    params.register_new_param(ptys.NumericParam , "sdr_chunk_sz"  ,     2**14 ,    1 ,   None ,    [1]                            )
    params.register_new_param(ptys.NumericParam , "spkr_volume"   ,       0.5 ,    0 ,    100 ,    [10,1]                         )
    params.register_new_param(ptys.NumericParam , "spkr_chunk_sz" ,     2**12 ,    1 ,   None ,    [1]                            )
    params.register_new_param(ptys.NumericParam , "spkr_fs"       ,     44100 ,    1 ,   None ,    [1]                            )

    return params

from scipy.signal import butter
def setup_lowpass(params):
    fmLpNum, fmLpDenom = butter(5, (params["sdr_dig_bw"] / 2) / (0.5 * params["sdr_fs"]), btype='low', analog=False)

    params.register_new_param(ptys.ObjParam, "sdr_lp_num", fmLpNum)
    params.register_new_param(ptys.ObjParam, "sdr_lp_denom", fmLpDenom)

import time
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

from system_pipeline_stages import ProvideRawRF, Filter, Downsample, RechunkArray, ReshapeArray, Endpoint, CalcDecibels
from async_pipeline         import FxApplyWorker, FxApplyWindow
def pipeline_worker(bridge, params):
    # Create loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    import time
    clock = time.time()
    def tick():
        nonlocal clock
        tmp = time.time()
        print(f"{tmp - clock}s")
        clock = tmp

    def demod(pdp):
        pdp.data = params["sdr_dec_fx"](pdp.data)

    # Set up and launch pipeline
    pipeline = AsyncPipeline(
        [ProvideRawRF(params["sdr"], params["sdr_chunk_sz"]),
         FxApplyWindow(demod),
         Filter(params["sdr_lp_num"], params["sdr_lp_denom"]),
         Downsample(params["sdr_fs"], params["spkr_fs"]),
         RechunkArray(params["spkr_chunk_sz"]),
         ReshapeArray((-1,1)),
         FxApplyWindow(lambda d : bridge.put(d.data)),
        #  FxApplyWindow(lambda d : tick()),
         Endpoint()]) 
    
    with open("key.out", "w") as f:
        for e in pipeline.stages:
            print(f"{e.gid} > {e.__class__.__name__}", file=f)
            
    pipeline.run_pipeline()

    loop.close()

if __name__ == "__main__":
    main()