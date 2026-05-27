#include <Servo.h>

// Pin configurations - adjust these to match your actual wiring
const int HORIZONTAL_SERVO_PIN = 9;       // Pin for horizontal (pan) servo
const int VERTICAL_SERVO_PIN = 10;        // Pin for vertical (tilt) servo
const int LASER_PIN = 11;                 // Pin for laser control

Servo horizontalServo;              // Servo object to control horizontal motor
Servo verticalServo;                // Servo object to control vertical motor

// Servo speed configurations
const int HORIZONTAL_STEP_DELAY_MS = 30;  // Milliseconds to wait per degree for horizontal (pan)
const int VERTICAL_STEP_DELAY_MS = 100;   // Milliseconds to wait per degree for vertical (tilt) - slower for heavy load

// Horizontal limits
const int HORIZONTAL_MIN = 60;            // Moderated minimum sweep angle (degrees)
const int HORIZONTAL_MAX = 120;           // Moderated maximum sweep angle (degrees)
const int HORIZONTAL_CENTER = 90;         // Center angle (degrees)

// Vertical limits (Restricted to safe range between 70 and 0 degrees)
const int VERTICAL_CENTER = 70;           // Physical right angle/resting position (upper limit)
const int VERTICAL_MIN = 50;              // Safe non-edge minimum angle (20 degrees of total travel)

int currentHorizontalAngle = HORIZONTAL_CENTER;
int currentVerticalAngle = VERTICAL_CENTER;

// Helper function declaration
void moveSlowly(Servo &servo, int &currentAngle, int targetAngle, int stepDelayMs);

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  Serial.println("--- Sentry Simple Dual Servo & Laser Test (Runs Once) ---");
  
  // Set up laser pin
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW); // Start with laser off

  // // Attach and set initial position of horizontal servo
  // horizontalServo.attach(HORIZONTAL_SERVO_PIN);
  // horizontalServo.write(currentHorizontalAngle);

  // Attach and set initial position of vertical servo
  verticalServo.attach(VERTICAL_SERVO_PIN);
  verticalServo.write(0);

  
  delay(1000); // Allow time for servos to reach initial positions

  horizontalServo.attach(HORIZONTAL_SERVO_PIN);
  // horizontalServo.write(80);
  //   digitalWrite(LASER_PIN, HIGH); // Start with laser off
  // verticalServo.write(10);

  //   delay(1000); // Allow time for servos to reach initial positions
  // horizontalServo.write(100);
  //   delay(1000); // Allow time for servos to reach initial positions
  // verticalServo.write(30);
  //     delay(1000); // Allow time for servos to reach initial positions

    // verticalServo.write(5);
    // delay(100);
    // verticalServo.write(10);
    // delay(100);
    // verticalServo.write(15);
    // delay(100);
    // verticalServo.write(20);
    // delay(100);
    // verticalServo.write(25);






  // // 1. Turn laser ON and move horizontal slowly to MAX
  // Serial.println("Laser ON. Moving horizontal slowly to MAX...");
  // digitalWrite(LASER_PIN, HIGH);
  // moveSlowly(horizontalServo, currentHorizontalAngle, HORIZONTAL_MAX, HORIZONTAL_STEP_DELAY_MS);
  // delay(500);

  // // 2. Move vertical slowly to MIN (50 degrees - gentle downward motion)
  // Serial.println("Moving vertical slowly to MIN (50 degrees)...");
  // moveSlowly(verticalServo, currentVerticalAngle, VERTICAL_MIN, VERTICAL_STEP_DELAY_MS);
  // delay(500);

  // // 3. Turn laser OFF and move horizontal slowly to MIN
  // Serial.println("Laser OFF. Moving horizontal slowly to MIN...");
  // digitalWrite(LASER_PIN, LOW);
  // moveSlowly(horizontalServo, currentHorizontalAngle, HORIZONTAL_MIN, HORIZONTAL_STEP_DELAY_MS);
  // delay(500);

  // // 4. Move vertical slowly back to CENTER (70 degrees - gentle upward motion)
  // Serial.println("Moving vertical slowly back to CENTER (70 degrees)...");
  // moveSlowly(verticalServo, currentVerticalAngle, VERTICAL_CENTER, VERTICAL_STEP_DELAY_MS);
  // delay(500);

  // // 5. Turn laser ON and return horizontal slowly to center
  // Serial.println("Laser ON. Returning horizontal slowly to center...");
  // digitalWrite(LASER_PIN, HIGH);
  // moveSlowly(horizontalServo, currentHorizontalAngle, HORIZONTAL_CENTER, HORIZONTAL_STEP_DELAY_MS);
  // delay(500);
  
  // 6. Turn laser OFF
 // digitalWrite(LASER_PIN, LOW);
  Serial.println("Laser OFF. Test completed.");
}

void loop() {
  // Empty - we do not repeat the test
}

// Function to move the servo slowly to a target angle
void moveSlowly(Servo &servo, int &currentAngle, int targetAngle, int stepDelayMs) {
  int step = (targetAngle > currentAngle) ? 1 : -1;
  while (currentAngle != targetAngle) {
    currentAngle += step;
    servo.write(currentAngle);
    delay(stepDelayMs);
  }
}