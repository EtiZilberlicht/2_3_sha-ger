#include <Servo.h>

// ===== Pins =====
const int HORIZONTAL_SERVO_PIN = 9;
const int VERTICAL_SERVO_PIN   = 10;
const int LASER_PIN            = 11;

// === angles ===
const int H_MIN = 0;
const int H_MAX = 130;
const int V_MIN = 0;
const int V_MAX = 70;
const int V_NEUTRAL_PULSE = 0;

Servo horizontalServo;
Servo verticalServo;

int currentHorizontalAngle = 75;
int currentVerticalAngle = 20;

const int INITIAL_HORIZONTAL_ANGLE = 75;
const int INITIAL_VERTICAL_ANGLE = 20;
const int LASER_OFF = LOW;

int clampHorizontal(int angle) {
  if (angle < H_MIN) return H_MIN;
  if (angle > H_MAX) return H_MAX;
  return angle;
}

int clampVertical(int angle) {
  if (angle < V_MIN) return V_MIN;
  if (angle > V_MAX) return V_MAX;
  return angle;
}

int verticalServoPulse(int logicalAngle) {
  int pulse = V_NEUTRAL_PULSE + clampVertical(logicalAngle);
  if (pulse < 0) return 0;
  if (pulse > 90) return 90;
  return pulse;
}

void writeVertical(int logicalAngle) {
  currentVerticalAngle = clampVertical(logicalAngle);
  verticalServo.write(verticalServoPulse(currentVerticalAngle));
}

void setup() {
  // פתיחת תקשורת מול פייתון
  Serial.begin(9600);

  // חיבור הסרווים לפינים
  horizontalServo.attach(HORIZONTAL_SERVO_PIN);
  verticalServo.attach(VERTICAL_SERVO_PIN);

  // הגדרת הלייזר כפלט
  pinMode(LASER_PIN, OUTPUT);

  // איפוס זוויות
  currentHorizontalAngle = INITIAL_HORIZONTAL_ANGLE;
  currentVerticalAngle = INITIAL_VERTICAL_ANGLE;

  horizontalServo.write(currentHorizontalAngle);
  writeVertical(currentVerticalAngle);

  turnLaserOff();
}

void moveHorizontalBy(int deltaAngle) {
  int targetAngle = clampHorizontal(currentHorizontalAngle + deltaAngle);
  horizontalServo.write(targetAngle);
  currentHorizontalAngle = targetAngle;
}

void moveVerticalBy(int deltaAngle) {
  writeVertical(currentVerticalAngle + deltaAngle);
}

// מזיז את המנוע האופקי בהדרגה, במקום ישירות - בקפיצות של 5 עם דיליי של 100 מילי שניות
void moveHorizontalBySmooth(int deltaAngle) {

  // חישוב זווית היעד
  int targetAngle = clampHorizontal(currentHorizontalAngle + deltaAngle);

  // כל עוד לא הגענו ליעד, ממשיכים להזיז את המנוע
  while (currentHorizontalAngle != targetAngle) {

    // אם צריך לגדול
    if (currentHorizontalAngle < targetAngle) {

      // קפיצה של 5 מעלות
      currentHorizontalAngle += 5;

      // אם עברנו את היעד בגלל הקפיצה, נתקן בדיוק ליעד
      if (currentHorizontalAngle > targetAngle) {
        currentHorizontalAngle = targetAngle;
      }

    } else {

      // אם צריך להקטין זווית
      currentHorizontalAngle -= 5;

      /*
       // תיקון במקרה שירדנו יותר מדי
      */
      if (currentHorizontalAngle < targetAngle) {
        currentHorizontalAngle = targetAngle;
      }
    }

    // הזזת המנוע לזווית החדשה
    horizontalServo.write(currentHorizontalAngle);

    // המתנה של 100 מילישניות
    delay(100);
  }
}

// מזיז את המנוע האנכי בצורה חלקה
void moveVerticalBySmooth(int deltaAngle) {

  // חישוב יעד חדש
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
    verticalServo.write(verticalServoPulse(currentVerticalAngle));
    delay(100);
  }
}

// מדליק את הלייזר
void turnLaserOn() {
  digitalWrite(LASER_PIN, HIGH);
}

// מכבה את הלייזר
void turnLaserOff() {
  digitalWrite(LASER_PIN, LOW);
}

void gotoAngles(int h, int v) {
  currentHorizontalAngle = clampHorizontal(h);
  horizontalServo.write(currentHorizontalAngle);
  writeVertical(v);
}

void resetToHome() {
  gotoAngles(INITIAL_HORIZONTAL_ANGLE, INITIAL_VERTICAL_ANGLE);
}

// מבצע "ירי" באמצעות 3 הבהובים של הלייזר
void fireLaser() {
  for (int i = 0; i < 3; i++) {

    // הדלקת לייזר
    turnLaserOn();
    delay(150);

    // כיבוי לייזר
    turnLaserOff();
    delay(150);
  }
}
void loop() {

  // בודקים אם הגיע מידע מהפייתון
  if (Serial.available() > 0) {

    // קוראים שורה מלאה עד ירידת שורה
    String command = Serial.readStringUntil('\n');

    // מנקה רווחים ו-enter מיותרים
    command.trim();

    // ===== FIRE =====
    if (command == "FIRE") {
      fireLaser();
    }

    // ===== LASER ON =====
    else if (command == "LASER_ON") {
      turnLaserOn();
    }

    // ===== LASER OFF =====
    else if (command == "LASER_OFF") {
      turnLaserOff();
    }

    else if (command == "RESET") {
      resetToHome();
    }

    else if (command.startsWith("G ")) {
      int sp = command.indexOf(' ', 2);
      if (sp > 0) {
        int h = command.substring(2, sp).toInt();
        int v = command.substring(sp + 1).toInt();
        gotoAngles(h, v);
      }
    }

    // ===== HORIZONTAL IMMEDIATE =====
    // דוגמא:
    // H 20
    else if (command.startsWith("H ")) {

      // לוקחים את כל מה שאחרי H
      String valueString = command.substring(2);

      // ממירים למספר
      int deltaAngle = valueString.toInt();

      // מזיזים מנוע אופקי
      moveHorizontalBy(deltaAngle);
    }

    // ===== VERTICAL IMMEDIATE =====
    // דוגמא:
    // V -20
    else if (command.startsWith("V ")) {

      String valueString = command.substring(2);
      int deltaAngle = valueString.toInt();

      moveVerticalBy(deltaAngle);
    }

    // ===== HORIZONTAL SMOOTH =====
    // דוגמא:
    // HS 40
    else if (command.startsWith("HS ")) {

      // substring(3) כי יש:
      // H S רווח
      String valueString = command.substring(3);

      int deltaAngle = valueString.toInt();

      moveHorizontalBySmooth(deltaAngle);
    }

    // ===== VERTICAL SMOOTH =====
    // דוגמא:
    // VS -40
    else if (command.startsWith("VS ")) {

      String valueString = command.substring(3);

      int deltaAngle = valueString.toInt();

      moveVerticalBySmooth(deltaAngle);
    }
  }
}