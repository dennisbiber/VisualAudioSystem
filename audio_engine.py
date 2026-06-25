import numpy as np
import soundfile as sf
import sounddevice as sd

# =========================================================
# AUDIO ENGINE
# =========================================================

class AudioEngine:

    def __init__(
        self,
        use_file=True,
        filename=None,
        device=None,
        samplerate=44100,
        blocksize=1024
    ):

        self.use_file = use_file
        self.device = device
        self.sr = samplerate
        self.chunk = blocksize

        # =========================
        # analysis outputs (same API)
        # =========================
        self.level = 0.0
        self.bass = 0.0
        self.transient = 0.0
        self.prev_energy = 0.0

        self.pos = 0

        # =========================
        # FILE MODE
        # =========================
        if self.use_file:

            if filename is None:
                raise ValueError("filename required when use_file=True")

            self.data, self.sr = sf.read(filename, dtype="float32")

            if self.data.ndim == 2:
                self.data = self.data.mean(axis=1)

            self.stream = sd.OutputStream(
                samplerate=self.sr,
                channels=1,
                callback=self._file_callback,
                blocksize=self.chunk
            )

        # =========================
        # LIVE INPUT MODE
        # =========================
        else:

            self.stream = sd.Stream(
                samplerate=self.sr,
                channels=1,
                device=(self.device, None),       # or None for default
                blocksize=self.chunk,
                callback=self._monitor_callback
            )

    # -----------------------------------------------------
    # start/stop
    # -----------------------------------------------------

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop()

    # -----------------------------------------------------
    # shared analysis
    # -----------------------------------------------------

    def _analyze(self, chunk):

        # RMS level
        self.level = float(np.sqrt(np.mean(chunk**2)))

        fft = np.abs(np.fft.rfft(chunk))

        # low freq energy
        self.bass = float(np.mean(fft[:20]))

        energy = float(np.mean(fft))
        self.transient = max(0.0, energy - self.prev_energy)
        self.prev_energy = energy

    # -----------------------------------------------------
    # callbacks
    # -----------------------------------------------------

    # file playback + analysis
    def _file_callback(self, outdata, frames, t, status):

        end = self.pos + frames
        chunk = self.data[self.pos:end]
        self.pos = end % len(self.data)

        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)))

        outdata[:, 0] = chunk
        self._analyze(chunk)

    def _monitor_callback(self, indata, outdata, frames, time, status):
        # Copy input to output (simple monitoring)
        outdata[:, 0] = indata[:, 0]
        
        # Also analyze for visuals
        chunk = indata.mean(axis=1)
        self._analyze(chunk)

    # live input only
    def _input_callback(self, indata, frames, t, status):

        chunk = indata.mean(axis=1)
        print(np.max(np.abs(chunk)))
        self._analyze(chunk)