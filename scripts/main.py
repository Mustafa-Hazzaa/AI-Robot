#!/usr/bin/env python3
import serial
import time
import requests
from motor_controller import MotorController

API_URL = "http://172.23.87.33:5000/decide"

def send_ai_command_to_arduino(mc, decision):
    """
    Convert AI JSON decision into Arduino command string and send it.
    Format: action,duration(ms),speed
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
    Execute a sequence of actions from the AI
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
    """Find Arduino on common ports and return the MotorController instance."""
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

def send_to_ai(distance):
    """Send distance to AI Flask API and return decision"""
    payload = {"distances": {"front": distance}, "speech": "move forward then righ rhen go backword"}
    try:
        response = requests.post(API_URL, json=payload, timeout=20)
        if response.status_code == 200:
            decisions = response.json()
            print("AI Decision Sequence:", decisions)
            return decisions
        else:
            print("AI server error:", response.text)
    except Exception as e:
        print("Failed to contact AI API:", e)
    return [{"action": "stop", "notes": "fallback decision"}]

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

            # 2️⃣ Send distance to AI and get action sequence
            action_sequence = send_to_ai(distance)

            # 3️⃣ Execute the ENTIRE action sequence
            execute_action_sequence(mc, action_sequence)
            
            # Wait before next sensor reading
            time.sleep(0.5)

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