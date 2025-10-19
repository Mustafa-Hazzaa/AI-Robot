#include "motor_control.h"
#include <Arduino.h>

// Pin definitions
const int ENA = 11;  // PWM pin
const int IN1 = 6;   // Digital pin
const int IN2 = 7;   // Digital pin
const int ENB = 10;  // PWM pin
const int IN3 = 8;   // Digital pin
const int IN4 = 9;   // Digital pin

// Helper to set motor directions + speed
void setMotor(bool in1, bool in2, bool in3, bool in4, int speed) {
    Serial.println("=== setMotor CALLED ===");
    Serial.print("IN1="); Serial.print(in1);
    Serial.print(" IN2="); Serial.print(in2);
    Serial.print(" IN3="); Serial.print(in3);
    Serial.print(" IN4="); Serial.print(in4);
    Serial.print(" ENA="); Serial.print(speed);
    Serial.print(" ENB="); Serial.println(speed);
    
    // Set direction pins
    digitalWrite(IN1, in1);
    digitalWrite(IN2, in2);
    digitalWrite(IN3, in3);
    digitalWrite(IN4, in4);
    
    // Set speed (PWM)
    analogWrite(ENA, speed);
    analogWrite(ENB, speed);
    
    // Verify the pins were set correctly
    Serial.print("Actual pins - IN1:"); Serial.print(digitalRead(IN1));
    Serial.print(" IN2:"); Serial.print(digitalRead(IN2));
    Serial.print(" IN3:"); Serial.print(digitalRead(IN3));
    Serial.print(" IN4:"); Serial.print(digitalRead(IN4));
    Serial.print(" ENA:"); Serial.print(analogRead(ENA));
    Serial.print(" ENB:"); Serial.println(analogRead(ENB));
}

void initMotors() {
    Serial.println("=== initMotors CALLED ===");
    
    // Set all pins as OUTPUT
    pinMode(ENA, OUTPUT);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(ENB, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    
    Serial.println("All motor pins set to OUTPUT");
    
    stopMotors();
    Serial.println("Motors initialized and stopped");
}

void stopMotors() {
    Serial.println("=== stopMotors CALLED ===");
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    Serial.println("All motors stopped");
}

void moveForward(int speed, int duration_ms) {
    Serial.println("=== moveForward CALLED ===");
    Serial.print("Speed: "); Serial.print(speed);
    Serial.print(" Duration: "); Serial.println(duration_ms);
    
    // Motor A: IN1 HIGH, IN2 LOW
    // Motor B: IN3 HIGH, IN4 LOW
    setMotor(HIGH, LOW, HIGH, LOW, speed);
    
    Serial.print("Moving forward for "); Serial.print(duration_ms); Serial.println(" ms");
    delay(duration_ms);
    
    Serial.println("Stopping after forward movement");
    stopMotors();
}

void moveBackward(int speed, int duration_ms) {
    Serial.println("=== moveBackward CALLED ===");
    // Motor A: IN1 LOW, IN2 HIGH
    // Motor B: IN3 LOW, IN4 HIGH
    setMotor(LOW, HIGH, LOW, HIGH, speed);
    delay(duration_ms);
    stopMotors();
}

void turnLeft(int speed, int duration_ms) {
    Serial.println("=== turnLeft CALLED ===");
    // Turn Left = Motor A Backward, Motor B Forward
    setMotor(LOW, HIGH, HIGH, LOW, speed);
    delay(duration_ms);
    stopMotors();
}

void turnRight(int speed, int duration_ms) {
    Serial.println("=== turnRight CALLED ===");
    // Turn Right = Motor A Forward, Motor B Backward
    setMotor(HIGH, LOW, LOW, HIGH, speed);
    delay(duration_ms);
    stopMotors(); 
}