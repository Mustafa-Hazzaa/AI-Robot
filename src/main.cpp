#include <Arduino.h>
#include "motor_control.h"
#include <NewPing.h>

// Ultrasonic pins
const int trigPin = 5;
const int echoPin = 4;
const int MAX_DISTANCE = 200;
NewPing sonar(trigPin, echoPin, MAX_DISTANCE);

void setup() {
  Serial.begin(9600);
  
  // Test serial communication immediately
  Serial.println("=== ARDUINO STARTING ===");
  
  // Initialize motors with debug
  Serial.println("Calling initMotors...");
  initMotors();
  Serial.println("initMotors completed");
  
  Serial.println("Arduino ready!");
}

void loop() {
  // Check if Pi sent something
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    Serial.print("Received: ");
    Serial.println(line);

    if (line == "REQ") {
      // Pi requested distance
      unsigned int distance = sonar.ping_cm();
      if (distance == 0 || distance > MAX_DISTANCE) distance = MAX_DISTANCE;
      Serial.println(distance);
    } 
    else {
      // Expecting motor command in format: action,duration,speed
      int firstComma = line.indexOf(',');
      int secondComma = line.lastIndexOf(',');
      
      Serial.print("First comma at: "); Serial.println(firstComma);
      Serial.print("Second comma at: "); Serial.println(secondComma);
      
      if (firstComma > 0 && secondComma > firstComma) {
        String action = line.substring(0, firstComma);
        int duration = line.substring(firstComma + 1, secondComma).toInt();
        int speed = line.substring(secondComma + 1).toInt();

        Serial.print("Parsed - Action: '");
        Serial.print(action);
        Serial.print("', Duration: ");
        Serial.print(duration);
        Serial.print(", Speed: ");
        Serial.println(speed);

        // All motor functions handle the delay and stopping
        Serial.print("Calling motor function for: ");
        Serial.println(action);
        
        if (action == "forward") {
          Serial.println("=== CALLING moveForward ===");
          moveForward(speed, duration);
          Serial.println("=== moveForward COMPLETED ===");
        }
        else if (action == "backward") {
          Serial.println("=== CALLING moveBackward ===");
          moveBackward(speed, duration);
        }
        else if (action == "left") {
          Serial.println("=== CALLING turnLeft ===");
          turnLeft(speed, duration);
        }
        else if (action == "right") {
          Serial.println("=== CALLING turnRight ===");
          turnRight(speed, duration);
        }
        else {
          Serial.println("=== CALLING stopMotors ===");
          stopMotors();
        }

        // Signal back to Pi
        Serial.println("DONE");
      } else {
        Serial.println("ERROR: Invalid command format");
        Serial.println("DONE");
      }
    }
  }
}