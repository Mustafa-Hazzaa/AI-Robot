#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <Arduino.h>

// Motor pins (L298N)
extern const int ENA, IN1, IN2;
extern const int ENB, IN3, IN4;

// Initialize pins
void initMotors();

// Stop motors
void stopMotors();

// Move commands
void moveForward(int speed, int duration_ms);
void moveBackward(int speed, int duration_ms);
void turnLeft(int speed, int duration_ms);
void turnRight(int speed, int duration_ms);
#endif
