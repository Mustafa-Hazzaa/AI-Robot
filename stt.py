# sst.py
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import pvporcupine
import struct
import time


class STT:
    # ... (Your existing Configs) ...
    ACCESS_KEY = "EYs0liZxZ+uvpvIgmLTkH9s8SObP93wN83Dv/5yzEuFRcoG6r0wq/A=="
    WAKE_WORD_PATH = "Wake_Word.ppn"
    SAMPLE_RATE = 16000
    MIC_NAME = "soundcore Liberty 4 NC"
    MODEL_SIZE = "small.en"
    SILENCE_THRESHOLD = 800
    SILENCE_DURATION = 2.0

    def __init__(self, callback):
        # The callback is the function that puts the audio into the queue
        self.callback = callback

        # --- Find mic ---
        # ... (Mic finding logic remains the same) ...
        self.mic_index = None
        for i, dev in enumerate(sd.query_devices()):
            if self.MIC_NAME in dev["name"] and dev["max_input_channels"] > 0:
                self.mic_index = i
                break

        if self.mic_index is None:
            raise RuntimeError(f"Microphone '{self.MIC_NAME}' not found.")

        print(f"🎧 Using microphone: {sd.query_devices(self.mic_index)['name']} (index {self.mic_index})")

        # --- Load Whisper ---
        print("🔄 Loading Whisper model...")
        self.model = WhisperModel(self.MODEL_SIZE, device="cpu", compute_type="int8")
        print("✅ Whisper model loaded.")

        # --- Load Porcupine ---
        print("🔄 Initializing Porcupine wake word...")
        self.porcupine = pvporcupine.create(
            access_key=self.ACCESS_KEY,
            keyword_paths=[self.WAKE_WORD_PATH]
        )
        print("✅ Wake word model loaded.")

        # --- State for continuous operation ---
        self.listening = True
        self.recording = False
        self.audio_buffer = []
        self.silence_counter = 0

    def normalize_audio(self, audio):
        audio = audio.astype(np.float32) / 32768.0
        max_amp = np.max(np.abs(audio))
        if max_amp > 0:
            audio = audio / max_amp
        return audio

    def model_transcribe(self, audio_data) -> str:
        """
        PERFORMS THE WHISPER TRANSCRIPTION. Called by the Worker Thread.
        """
        print("🎙️ Transcribing...")
        audio_float = self.normalize_audio(audio_data)
        segments, info = self.model.transcribe(audio_float, beam_size=5)
        text = " ".join(segment.text for segment in segments)
        print(f"🧠 Transcription Result: {text}")
        return text

    def process_audio(self, audio_data):
        """
        Called when a command is finished recording. 
        Passes the raw audio array to the callback (which queues it).
        """
        self.callback(audio_data)

    def audio_callback(self, indata, frames, time_info, status):
        # This function MUST be fast! It runs in the real-time audio thread.

        if status:
            # We still print the warning, but queuing should prevent it from happening often
            print(f"Audio Stream Status: {status}")

        pcm = struct.unpack_from("h" * self.porcupine.frame_length, indata.tobytes())
        keyword_index = self.porcupine.process(pcm)

        if keyword_index >= 0:
            print("\n🔊 Wake word detected! Start speaking...")
            self.recording = True
            self.audio_buffer.clear()
            self.silence_counter = 0

        if self.recording:
            # Append the whole frame data for transcription
            self.audio_buffer.extend(indata[:, 0])

            if np.max(np.abs(indata)) < self.SILENCE_THRESHOLD:
                self.silence_counter += frames / self.SAMPLE_RATE
            else:
                self.silence_counter = 0

            if self.silence_counter >= self.SILENCE_DURATION:
                self.recording = False
                audio_array = np.array(self.audio_buffer, dtype=np.int16)
                self.process_audio(audio_array)  # Calls the queueing function in main.py
                self.audio_buffer.clear()
                self.silence_counter = 0
                print("\n🎧 Listening for wake word...")

    def start_listening(self):
        """Starts the blocking audio stream in a background thread."""
        print("🎧 Starting continuous audio stream...")
        with sd.InputStream(
                device=self.mic_index,
                channels=1,
                samplerate=self.SAMPLE_RATE,
                blocksize=self.porcupine.frame_length,
                dtype="int16",
                callback=self.audio_callback
        ):
            while self.listening:
                sd.sleep(100)