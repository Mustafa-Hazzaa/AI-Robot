#!/usr/bin/env python3
import serial
import time
import requests
from motor_controller import MotorController

# --- CHANGE 1: Define the host, not the full URL ---
API_HOST = "http://172.24.154.33:5000"

def send_ai_command_to_arduino(mc, decision):
    """
    Convert AI JSON decision into Arduino command string and send it.
    (This function is unchanged)
    """
    action = decision.get("action", "stop")
    duration_sec = decision.get("duration")
    if duration_sec is None or duration_sec <= 0:
        duration_sec = 1  # default 1 second
    speed = decision.get("speed")
    if speed is None:
        speed = 180  # default speed

    duration_ms = int(duration_sec * 1000) if action != "stop" else 1000
    speed = 0 if action == "stop" else speed

    command_str = f"{action},{duration_ms},{speed}"
    print(f"Sending to Arduino: {command_str}")
    mc.send_action(command_str)

def execute_action_sequence(mc, action_sequence):
    """
    Execute a sequence of actions from the AI.
    (This function is unchanged)
    """
    if not action_sequence:
        print("No actions to execute")
        return
    
    print(f"Executing {len(action_sequence)} actions:")
    for i, action in enumerate(action_sequence):
        print(f"  {i+1}. {action}")
    
    # Execute each action in sequence
    for i, action in enumerate(action_sequence):
        print(f"\n--- Executing action {i+1}/{len(action_sequence)}: {action['action']} ---")
        send_ai_command_to_arduino(mc, action)
        time.sleep(0.2)  # Small delay between actions

def check_the_arduino():
    """
    Find Arduino on common ports and return the MotorController instance.
    (This function is unchanged)
    """
    ports = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0']
    for port in ports:
        try:
            print(f"Trying {port}...")
            mc = MotorController(port=port)
            print(f"Connected to Arduino on {port}")
            return mc
        except Exception:
            continue
    print("Could not find Arduino!")
    return None

# --- CHANGE 2: Old send_to_ai function is removed ---

# --- CHANGE 3: New function to submit state ---
def submit_state_to_server(distance_cm):
    """Send sensor data to the server."""
    payload = {"distances": {"front": distance_cm}}
    try:
        requests.post(f"{API_HOST}/submit_state", json=payload, timeout=1.0)
    except Exception as e:
        print(f"Failed to submit state: {e}")

# --- CHANGE 4: New function to fetch a plan ---
def fetch_plan_from_server():
    """Ask the server if there is a new command plan."""
    try:
        response = requests.get(f"{API_HOST}/get_command", timeout=1.0)
        if response.status_code == 200:
            action_sequence = response.json()
            if action_sequence:  # Will be [] if no new plan
                return action_sequence
    except Exception as e:
        print(f"Failed to get command: {e}")
    return None  # No new plan

# --- CHANGE 5: Updated main loop ---
def loop(mc):
    while True:
        try:
            # 1️⃣ Request distance from Arduino
            distance = mc.get_distance()
            
            if distance is None:
                print("Failed to get valid distance.")
                time.sleep(0.5)
                continue

            print(f"Distance: {distance:.2f} cm")

            # 2️⃣ Submit our state to the server
            submit_state_to_server(distance)

            # 3️⃣ Ask the server for a new plan
            action_sequence = fetch_plan_from_server()

            # 4️⃣ If we got one, execute it
            if action_sequence:
                print("✅ --- New Plan Received! Executing... ---")
                execute_action_sequence(mc, action_sequence)
                print("✅ --- Plan Finished. ---")
            
            # Wait a short time before polling again
            time.sleep(0.2)

        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    mc = check_the_arduino()
    if mc:
        loop(mc)
