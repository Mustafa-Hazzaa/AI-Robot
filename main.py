# main.py
from flask import Flask, jsonify, request
from stt import STT
from AI import AIPlanner  # Make sure your AI.py file is named AI.py or change this
import threading
import time
from queue import Queue
import json
import numpy as np
import queue  # Import the standard queue module

app = Flask(__name__)

# --- Thread-Safe Global State ---
# We need to store the Pi's latest state and the newest plan
g_current_distances = {"front": 100.0}
g_state_lock = threading.Lock()
g_plan_queue = Queue()  # Holds complete plans for the Pi
# --------------------------------

# Initialize modules
ai = AIPlanner()

# Initialize a Queue for audio arrays waiting to be processed
audio_queue = Queue()


def worker_thread(audio_queue: Queue, ai_planner: AIPlanner, stt_instance: STT):
    """
    A dedicated thread that handles the heavy processing (Whisper/LLM).
    """
    print("👷 Worker thread started, waiting for audio commands...")
    while True:
        # Blocks until an audio array is available
        # --- FIX 1: Only get audio_array, not distances ---
        audio_array = audio_queue.get()

        # 1. Perform transcription (heavy task)
        transcript = stt_instance.model_transcribe(audio_array)

        # 2. Clean the Transcribed Command Input
        cleaned_transcript = transcript.strip().lower()
        if cleaned_transcript.endswith('.'):
            cleaned_transcript = cleaned_transcript[:-1]

        if not cleaned_transcript:
            print("🎙️ Heard empty audio, ignoring.")
            audio_queue.task_done()
            continue

        # 3. Get the most recent sensor data from our global state
        with g_state_lock:
            local_distances = g_current_distances.copy()

        print(f"\n✨ Worker Processing: '{cleaned_transcript}' with distances {local_distances}")

        # 4. Perform AI planning (heavy task)
        try:
            plan = ai_planner.generate_plan(cleaned_transcript, local_distances)

            # 5. Put the finished plan on the queue for the Pi to fetch
            g_plan_queue.put(plan)

            print("\n🤖 GENERATED PLAN (waiting for Pi to fetch):")
            print(json.dumps(plan, indent=2))

        except Exception as e:
            print(f"❌ Worker Error during plan generation: {e}")

        audio_queue.task_done()


# --- FIX 2: Corrected function signature ---
def command_callback_queue(audio_array: np.ndarray):
    """
    Lightweight callback from STT. Just puts the audio in the queue.
    """
    # Put the heavy task data (audio) into the queue
    audio_queue.put(audio_array)
    print("📝 Command audio recorded and queued for processing.")


# Initialize SST and pass the lightweight queuing callback function
stt = STT(callback=command_callback_queue)


@app.route("/")
def index():
    return "🤖 Autonomous Robot MCP running (Voice command worker active)"


# --- NEW ENDPOINT 1 ---
@app.route("/submit_state", methods=["POST"])
def submit_state():
    """
    Called by the Raspberry Pi very frequently to report its sensor data.
    """
    try:
        data = request.get_json(force=True)
        with g_state_lock:
            global g_current_distances
            g_current_distances = data.get("distances", {"front": 100.0})
        # print(f"State update: {g_current_distances}") # Uncomment for debugging
        return jsonify({"status": "received"})
    except Exception as e:
        print(f"❌ Error in /submit_state: {e}")
        return jsonify({"error": str(e)}), 500


# --- NEW ENDPOINT 2 ---
@app.route("/get_command", methods=["GET"])
def get_command():
    """
    Called by the Raspberry Pi in its loop, asking "any new plans for me?"
    """
    try:
        # Try to get a plan from the queue without blocking
        plan = g_plan_queue.get_nowait()
        return jsonify(plan)
    except queue.Empty:
        # This is normal. It just means no new voice command has been processed.
        return jsonify([])  # Return an empty list
    except Exception as e:
        print(f"❌ Error in /get_command: {e}")
        return jsonify({"error": str(e)}), 500


# --- OLD /decide ENDPOINT IS REMOVED ---


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
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)