#!/usr/bin/env python3
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time
import os
from datetime import datetime
import queue

# -----------------------------
# CONFIG
# -----------------------------
DEVICE_NAME = "USB Audio Device"
CHUNK_DURATION = 4.0 # Seconds of audio to save per file
MAX_FILES = 20# Max files to keep in the queue directory
OUTPUT_DIR = "data/audio_queue" # Directory to save audio chunks
# Note: BLOCKSIZE is now calculated based on samplerate and CHUNK_DURATION
# -----------------------------

# Global variables for the stream
stream_data = {'buffer': [], 'recording': False, 'SAMPLE_RATE': None}
audio_queue = queue.Queue()


def get_mic_info():
    """Detects the USB mic and its sample rate."""
    for i, d in enumerate(sd.query_devices()):
        if DEVICE_NAME.lower() in d["name"].lower() and d["max_input_channels"] > 0:
            sr = int(d["default_samplerate"])
            print(f"✅ Found USB mic: {d['name']} (device {i}), samplerate: {sr}")
            return i, sr
    print("❌ USB mic not found!")
    return None, None


def audio_callback(indata, frames, time_info, status):
    """Callback function for the sounddevice stream."""
    if status:
        # This will still print overflow warnings, but the buffer is larger now
        print("⚠️ Audio Stream Status:", status) 

    if stream_data['recording']:
        # Put the chunk in a queue for the main thread to handle file writing
        try:
            audio_queue.put_nowait(indata.copy())
        except queue.Full:
            pass # Drop chunk if queue is full


def file_writer_loop():
    """Writes chunks from the queue to files in the background."""
    print("✍️ File writer loop started.")
    
    # Calculate block size for the duration
    BLOCKSIZE = int(stream_data['SAMPLE_RATE'] * CHUNK_DURATION)
    
    # Pre-allocate buffer based on the required duration
    current_buffer = []

    while True:
        try:
            # Get data chunk (non-blocking, short timeout)
            chunk = audio_queue.get(timeout=0.1) 
            current_buffer.append(chunk)

        except queue.Empty:
            # If queue is empty, loop and wait for more data
            time.sleep(0.01)
            continue

        # Check if the buffer is full enough to write a file
        if len(current_buffer) * chunk.shape[0] >= BLOCKSIZE:
            
            # Concatenate only the required amount of data
            audio_data = np.concatenate(current_buffer, axis=0)[:BLOCKSIZE]
            current_buffer = [] # Reset buffer (or keep overflow if needed)

            # Create the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filepath = os.path.join(OUTPUT_DIR, f"{timestamp}.wav")

            # Write the file
            sf.write(filepath, audio_data, stream_data['SAMPLE_RATE'])
            print(f"➡️ Saved: {filepath}")

            # Optional: Simple garbage collection for old files (if transcriber fails)
            files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.wav')])
            if len(files) > MAX_FILES:
                os.remove(os.path.join(OUTPUT_DIR, files[0]))
                print(f"🧹 Cleaned up oldest file: {files[0]}")


def main():
    mic_index, sr = get_mic_info()
    if mic_index is None:
        return

    stream_data['SAMPLE_RATE'] = sr
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Start the thread responsible for converting queue data to files
    threading.Thread(target=file_writer_loop, daemon=True).start()
    
    # Start the audio stream
    stream_data['recording'] = True
    print("🎧 Listening... Press Ctrl+C to stop.")
    
    # Set the blocksize smaller for faster filling of the file writer buffer
    callback_blocksize = 4096 
    
    try:
        with sd.InputStream(device=mic_index,
                            channels=1,
                            samplerate=sr,
                            blocksize=callback_blocksize,
                            callback=audio_callback):
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Stopped audio recording.")
    finally:
        stream_data['recording'] = False

if __name__ == "__main__":
    main()