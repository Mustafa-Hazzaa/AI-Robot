#!/usr/bin/env python3
import whisper
import librosa
import os
import time
import soundfile as sf
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------
MODEL_NAME = "tiny" # smallest and fastest for Pi
TARGET_SR = 16000# Whisper preferred sample rate
INPUT_DIR = "data/audio_queue"
# -----------------------------


def transcribe_file(filepath, model):
    """Loads, resamples, and transcribes a single audio file."""
    
    print(f"⏳ Processing: {os.path.basename(filepath)}")
    start_time = time.time()
    
    try:
        # Load audio and resample directly in one step (using librosa.load)
        # Note: librosa loads as TARGET_SR by default if sr is specified
        audio, sr_orig = librosa.load(filepath, sr=TARGET_SR)
        
        # Transcribe using Whisper
        # Since librosa loads it into a numpy array, you can pass the array directly
        # Whisper automatically resamples if needed, but it's often cleaner to
        # do it explicitly with librosa for better quality, which we did above.
        result = model.transcribe(audio, fp16=False)
        
        elapsed_time = time.time() - start_time
        print(f"🗣️ Transcribed ({elapsed_time:.2f}s): {result['text']}")
        
    except Exception as e:
        print(f"❌ Error transcribing {filepath}: {e}")
        result = {'text': ''}
        
    # After processing, delete the file to prevent re-transcription
    os.remove(filepath)
    print(f"🗑️ Cleaned up {os.path.basename(filepath)}")
    
    return result


def main():
    # Load Whisper model once
    print("🔍 Loading Whisper model...")
    model = whisper.load_model(MODEL_NAME)
    print("✅ Whisper model loaded.")

    # Ensure input directory exists
    if not os.path.isdir(INPUT_DIR):
        print(f"❌ Input directory '{INPUT_DIR}' not found. Run audio_recorder.py first.")
        return

    print("🤖 AI Transcriber running. Waiting for audio files...")

    while True:
        # Find all WAV files in the queue directory
        files_to_process = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith('.wav')])
        
        if files_to_process:
            # Process the oldest file first (FIFO)
            oldest_file = os.path.join(INPUT_DIR, files_to_process[0])
            transcribe_file(oldest_file, model)
        else:
            # If no files, wait a moment before checking again
            time.sleep(0.5)

if __name__ == "__main__":
    main()