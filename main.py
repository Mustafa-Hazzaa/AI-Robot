# main.py
from flask import Flask, jsonify, request
from stt import STT
from AI import AIPlanner
import threading
import time
from queue import Queue
import json
import numpy as np

app = Flask(__name__)

# Initialize modules
ai = AIPlanner()

# Initialize a Queue for audio arrays waiting to be processed
audio_queue = Queue()


# --- Placeholder for Real Ultrasonic Data ---
# In a real robot, this would be read from a sensor hardware interface.
def get_ultrasonic_data():
    """Simulates getting the latest sensor readings."""
    # This must be a fast, non-blocking read!
    return {"front": 0.52, "left": 1.2, "right": 0.9}


def worker_thread(audio_queue: Queue, ai_planner: AIPlanner, stt_instance: STT):
    """
    A dedicated thread that handles the heavy processing (Whisper/LLM).
    """
    print("👷 Worker thread started, waiting for commands...")
    while True:
        # Blocks until an item is available: (audio_array, distances)
        audio_array, distances = audio_queue.get()

        # 1. Perform transcription (heavy task)
        transcript = stt_instance.model_transcribe(audio_array)

        # --- NEW: Clean the Transcribed Command Input ---
        # 1. Remove leading/trailing whitespace (e.g., ' Move forward.' -> 'Move forward.')
        cleaned_transcript = transcript.strip()

        # 2. Optionally, remove trailing common punctuation to further normalize
        # (e.g., 'Move forward.' -> 'Move forward')
        if cleaned_transcript.endswith('.'):
            cleaned_transcript = cleaned_transcript[:-1]

        # 3. Make it lowercase (LLMs often perform better with normalized input)
        cleaned_transcript = cleaned_transcript.lower()
        # Example: 'move forward'

        # 2. Perform AI planning (heavy task)
        print(f"\n✨ Worker Processing Cleaned Command: '{cleaned_transcript}'")
        try:
            # Use the cleaned_transcript here!
            plan = ai_planner.generate_plan(cleaned_transcript, distances)

            # 3. Handle the generated plan (THIS IS YOUR API REQUEST SUCCESS)
            import json
            print("\n🤖 GENERATED PLAN (to be executed by robot):")
            print(json.dumps(plan, indent=2))

        except Exception as e:
            # Note: The output cleaning logic in AI.py should still be there
            # as a backup for the LLM's output.
            print(f"❌ Worker Error during plan generation: {e}")

        audio_queue.task_done()


def command_callback_queue(audio_array: np.ndarray):
    """
    This function is executed by the background SST thread
    whenever a full command is recorded (NO TRANSCRIPTION HERE).
    It just queues the data.
    """
    # 1. Get current sensor data (lightweight read)
    distances = get_ultrasonic_data()

    # 2. Put the heavy task data (audio + sensor data) into the queue
    audio_queue.put((audio_array, distances))
    print("📝 Command recorded and queued for processing.")


# Initialize SST and pass the lightweight queuing callback function
stt = STT(callback=command_callback_queue)


@app.route("/")
def index():
    return "🤖 Autonomous Robot MCP running (Voice command worker active)"


@app.route("/decide", methods=["POST"])
def decide():
    # This endpoint remains for debugging/manual API calls
    return jsonify({"status": "Voice control is backgrounded. Command processing handled by worker thread."})


if __name__ == "__main__":
    # 1. Start the dedicated worker thread for heavy tasks
    worker = threading.Thread(target=worker_thread, args=(audio_queue, ai, stt), daemon=True)
    worker.start()

    # 2. Start the SST continuous listening loop in a separate thread
    stt_thread = threading.Thread(target=stt.start_listening, daemon=True)
    stt_thread.start()
    print("🚀 SST Listening and Worker threads started...")

    # 3. Start the Flask server in the main thread
    print("🌐 Flask server starting...")
    # debug=False and use_reloader=False are essential when using threading
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)