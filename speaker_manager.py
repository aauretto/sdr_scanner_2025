import sounddevice as sd
import numpy as np
from queue import Queue, Empty
import threading

class SpeakerManager():
    def __init__(self, sampRate = 44100, blockSize = 2**12, chunkSrc = None):
        self.chunkSrc  = chunkSrc
        self.blockSize = blockSize
        self.sampRate  = sampRate
        self.stream    = None
        self.isInit    = False

    def set_source(self, chunkSrc : Queue):
        self.chunkSrc = chunkSrc

    def init_stream(self):

        if not self.chunkSrc:
            raise RuntimeError("Invalid SpeakerManager source of data")

        def audio_callback(outdata, frames, time, status):
            try:
                data = self.chunkSrc.get_nowait()
            except Empty:
                outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                print("Missed a chunk")
            else:
                outdata[:] = data

        self.stream = sd.OutputStream(
            samplerate=self.sampRate,
            blocksize=self.blockSize,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        self.isInit = True

    def start(self): 
        if not self.isInit:
            raise RuntimeError("Tried to start uninitialized stream")
        self.stream.start()

    def stop(self):
        self.stream.stop()
        self.stream.close()


import time
def __testing():
    q = Queue()
    bs = 2**12
    fs = 44100

    sm = SpeakerManager(blockSize=bs, sampRate=fs)
    sm.set_source(q)

    freq = 440  # Hz

    def generate_sine_wave():
        t = np.linspace(0, bs / fs, bs, endpoint=False)
        while True:
            wave = 0.1 * np.sin(2 * np.pi * freq * t).astype(np.float32)
            q.put(wave.reshape(-1, 1))
    threading.Thread(target=generate_sine_wave, daemon=True).start()

    sm.init_stream()
    sm.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sm.stop()


if __name__ == "__main__":
    __testing()