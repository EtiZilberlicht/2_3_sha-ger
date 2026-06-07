#include <Servo.h>

// ===== Pins =====
const int HORIZONTAL_SERVO_PIN = 9;
const int VERTICAL_SERVO_PIN   = 10;
const int LASER_PIN            = 11;

// ===== Servo Angle Limits and Defaults =====
const int H_MIN = 0;
const int H_MAX = 130;
const int V_MIN = 0;
const int V_MAX = 90;

const int INITIAL_HORIZONTAL_ANGLE = 80;
const int INITIAL_VERTICAL_ANGLE   = 20;

// Pulse configuration for vertical servo
const int V_NEUTRAL_PULSE = 0;

// ===== Servo Instances =====
Servo horizontalServo;
Servo verticalServo;

// ===== Global State =====
int currentHorizontalAngle = INITIAL_HORIZONTAL_ANGLE;
int currentVerticalAngle   = INITIAL_VERTICAL_ANGLE;

// ===== Function Prototypes =====
int clampHorizontal(int angle);
int clampVertical(int angle);
int verticalServoPulse(int logicalAngle);
void writeHorizontal(int logicalAngle);
void writeVertical(int logicalAngle);
void turnLaserOn();
void turnLaserOff();
void moveHorizontalBy(int deltaAngle);
void moveVerticalBy(int deltaAngle);
void moveHorizontalBySmooth(int deltaAngle);
void moveVerticalBySmooth(int deltaAngle);
void gotoAngles(int h, int v);
void resetToHome();
void fireLaser();

// ===== Setup & Loop =====

void setup() {
  // Initialize serial communication with Python at 9600 baud
  Serial.begin(9600);

  // Attach servos to their control pins
  horizontalServo.attach(HORIZONTAL_SERVO_PIN);
  verticalServo.attach(VERTICAL_SERVO_PIN);

  // Configure laser pin as output
  pinMode(LASER_PIN, OUTPUT);

  // Initialize servos to their default starting positions
  writeHorizontal(INITIAL_HORIZONTAL_ANGLE);
  writeVertical(INITIAL_VERTICAL_ANGLE);

  // Ensure the laser starts in the OFF state
  turnLaserOff();
}

void loop() {
  // Process incoming commands from Python if serial data is available
  if (Serial.available() > 0) {
    // Read the command string until a newline character
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "FIRE") {
      fireLaser();
    }
    else if (command == "LASER_ON") {
      turnLaserOn();
    }
    else if (command == "LASER_OFF") {
      turnLaserOff();
    }
    else if (command == "RESET") {
      resetToHome();
    }
    else if (command.startsWith("G ")) {
      // Parse goto command: "G <h_angle> <v_angle>"
      int sp = command.indexOf(' ', 2);
      if (sp > 0) {
        int h = command.substring(2, sp).toInt();
        int v = command.substring(sp + 1).toInt();
        gotoAngles(h, v);
      }
    }
    else if (command.startsWith("HS ")) {
      // Parse smooth horizontal relative move: "HS <delta>"
      int deltaAngle = command.substring(3).toInt();
      moveHorizontalBySmooth(deltaAngle);
    }
    else if (command.startsWith("VS ")) {
      // Parse smooth vertical relative move: "VS <delta>"
      int deltaAngle = command.substring(3).toInt();
      moveVerticalBySmooth(deltaAngle);
    }
    else if (command.startsWith("H ")) {
      // Parse immediate horizontal relative move: "H <delta>"
      int deltaAngle = command.substring(2).toInt();
      moveHorizontalBy(deltaAngle);
    }
    else if (command.startsWith("V ")) {
      // Parse immediate vertical relative move: "V <delta>"
      int deltaAngle = command.substring(2).toInt();
      moveVerticalBy(deltaAngle);
    }
  }
}

// ===== Helper Functions Implementation =====

// Clamps the horizontal angle to stay within allowed physical limits [H_MIN, H_MAX]
int clampHorizontal(int angle) {
  if (angle < H_MIN) return H_MIN;
  if (angle > H_MAX) return H_MAX;
  return angle;
}

// Clamps the vertical angle to stay within allowed physical limits [V_MIN, V_MAX]
int clampVertical(int angle) {
  if (angle < V_MIN) return V_MIN;
  if (angle > V_MAX) return V_MAX;
  return angle;
}

// Computes the actual pulse/angle to write to the vertical servo
int verticalServoPulse(int logicalAngle) {
  int pulse = V_NEUTRAL_PULSE + clampVertical(logicalAngle);
  if (pulse < 0) return 0;
  if (pulse > 90) return 90;
  return pulse;
}

// Writes a target angle to the horizontal servo, clamping it first
void writeHorizontal(int logicalAngle) {
  currentHorizontalAngle = clampHorizontal(logicalAngle);
  horizontalServo.write(currentHorizontalAngle);
}

// Writes a target angle to the vertical servo, clamping and converting it first
void writeVertical(int logicalAngle) {
  currentVerticalAngle = clampVertical(logicalAngle);
  verticalServo.write(verticalServoPulse(currentVerticalAngle));
}

// Turns the laser pin HIGH (ON)
void turnLaserOn() {
  digitalWrite(LASER_PIN, HIGH);
}

// Turns the laser pin LOW (OFF)
void turnLaserOff() {
  digitalWrite(LASER_PIN, LOW);
}

// ===== Action Functions Implementation =====

// Immediately moves the horizontal servo by a relative delta angle
void moveHorizontalBy(int deltaAngle) {
  writeHorizontal(currentHorizontalAngle + deltaAngle);
}

// Immediately moves the vertical servo by a relative delta angle
void moveVerticalBy(int deltaAngle) {
  writeVertical(currentVerticalAngle + deltaAngle);
}

// Smoothly transitions the horizontal servo by a relative delta angle in steps of 5 degrees
void moveHorizontalBySmooth(int deltaAngle) {
  int targetAngle = clampHorizontal(currentHorizontalAngle + deltaAngle);

  while (currentHorizontalAngle != targetAngle) {
    if (currentHorizontalAngle < targetAngle) {
      currentHorizontalAngle += 5;
      if (currentHorizontalAngle > targetAngle) {
        currentHorizontalAngle = targetAngle;
      }
    } else {
      currentHorizontalAngle -= 5;
      if (currentHorizontalAngle < targetAngle) {
        currentHorizontalAngle = targetAngle;
      }
    }
    horizontalServo.write(currentHorizontalAngle);
    delay(100);
  }
}

// Smoothly transitions the vertical servo by a relative delta angle in steps of 5 degrees
void moveVerticalBySmooth(int deltaAngle) {
  int targetAngle = clampVertical(currentVerticalAngle + deltaAngle);

  while (currentVerticalAngle != targetAngle) {
    if (currentVerticalAngle < targetAngle) {
      currentVerticalAngle += 5;
      if (currentVerticalAngle > targetAngle) {
        currentVerticalAngle = targetAngle;
      }
    } else {
      currentVerticalAngle -= 5;
      if (currentVerticalAngle < targetAngle) {
        currentVerticalAngle = targetAngle;
      }
    }
    writeVertical(currentVerticalAngle);
    delay(100);
  }
}

// Moves both servos to absolute target angles
void gotoAngles(int h, int v) {
  writeHorizontal(h);
  writeVertical(v);
}

// Resets both servos to their default starting home positions
void resetToHome() {
  gotoAngles(INITIAL_HORIZONTAL_ANGLE, INITIAL_VERTICAL_ANGLE);
}

// Simulates a firing sequence by blinking the laser 3 times
void fireLaser() {
  for (int i = 0; i < 3; i++) {
    turnLaserOn();
    delay(150);
    turnLaserOff();
    delay(150);
  }
}