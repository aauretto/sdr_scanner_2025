

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
    params = init_params()
    setup_sdr(params)
    setup_lowpass(params)
    bridgeFromPipeline = Queue()

    pipelineThread = Thread(target=pipeline_worker, args = (bridgeFromPipeline, params))
    # Insert a process here that does screen (needs metadata from pipeline window)
    # Wrap button manager and screen into single hw driver process?
    # btnMgr = setup_btns()

    sm = SpeakerManager(blockSize=params["spkr_chunk_sz"], sampRate=params["spkr_fs"])
    sm.set_source(bridgeFromPipeline)
    sm.init_stream()
    sm.start()

    pipelineThread.start()
    pipelineThread.join()

    sm.stop()
    
# def setup_btns():
#     """
#     Sets up buttons.
#     Returns manager that runs buttons
#     """
#     import hw_interface.button_handler as bh
#     btnCfg = [
#         #    pin    Event     Press
#             (11  ,  "M3"    , bh.PRESS_TYPE.DOWN) ,
#             (13  ,  "M2"    , bh.PRESS_TYPE.DOWN) ,
#             (15  ,  "M1"    , bh.PRESS_TYPE.DOWN) ,
#             (29  ,  "ok"    , bh.PRESS_TYPE.DOWN) ,
#             (31  ,  "right" , bh.PRESS_TYPE.DOWN) ,
#             (33  ,  "left"  , bh.PRESS_TYPE.DOWN) ,
#             (35  ,  "down"  , bh.PRESS_TYPE.UP) ,
#             (37  ,  "up"    , bh.PRESS_TYPE.CASCADE) ,
#             ]

#     bh.setup_hw()

#     mpManager = bh.MPbtnWrapper()
#     mpManager.register_btns(btnCfg)
#     mpManager.start()

#     return mpManager 

def init_params():
    """
    Set up initial parameters for the scanner
    """
    from demodulation import DECODE_FM

    sysPs = sps.SysParams()

    # ========================================================================================================================== #
    #                          Type of param      Name              InitVal    Min      Max      StepSizes                       #
    # ========================================================================================================================== #
    sysPs.register_new_param(ptys.NumericParam , "sdr_cf"        ,    88.3e6 , 24e6 , 1766e6 ,    [1e4,1e5,1e6,1e7,1e8,1e9,1e2,1e3]  )
    sysPs.register_new_param(ptys.NumericParam , "sdr_fs"        ,    0.25e6 ,    0 ,    2e9 ,     None                          )
    sysPs.register_new_param(ptys.NumericParam , "sdr_dig_bw"    ,     150e3 ,  1e3 ,  250e3 ,    [10e3,100e3,1e3]               )
    sysPs.register_new_param(ptys.FuncParam    , "sdr_dec_fx"    , DECODE_FM ,                                                   )
    sysPs.register_new_param(ptys.NumericParam , "sdr_squelch"   ,       -20 ,  -40 ,      1 ,    [10, 0.001, 0.1, 1]            )
    sysPs.register_new_param(ptys.NumericParam , "sdr_chunk_sz"  ,     2**14 ,    1 ,   None ,    [1]                            )
    sysPs.register_new_param(ptys.NumericParam , "spkr_volume"   ,       0.5 ,    0 ,    100 ,    [10,1]                         )
    sysPs.register_new_param(ptys.NumericParam , "spkr_chunk_sz" ,     2**12 ,    1 ,   None ,    [1]                            )
    sysPs.register_new_param(ptys.NumericParam , "spkr_fs"       ,     44100 ,    1 ,   None ,    [1]                            )

    return sysPs

from scipy.signal import butter
def setup_lowpass(params):
    fmLpNum, fmLpDenom = butter(5, (params["sdr_dig_bw"] / 2) / (0.5 * params["sdr_fs"]), btype='low', analog=False)

    params.register_new_param(ptys.ObjParam, "sdr_lp_num", fmLpNum)
    params.register_new_param(ptys.ObjParam, "sdr_lp_denom", fmLpDenom)

def setup_sdr(params):
    sdr = RtlSdr()

    # Configure SDR
    sdr.center_freq = params["sdr_cf"].get()
    sdr.sample_rate = params["sdr_fs"].get()
    sdr.freq_correction = 60
    sdr.gain = 'auto'

    params["sdr_cf"].set(sdr.get_sample_rate())
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