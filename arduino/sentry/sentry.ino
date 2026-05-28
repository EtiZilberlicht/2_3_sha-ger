#include <Servo.h>

// ===== Pins =====
const int HORIZONTAL_SERVO_PIN = 9;
const int VERTICAL_SERVO_PIN   = 10;
const int LASER_PIN            = 11;

// === angles ===
const int MIN_ANGLE = 0;
const int MAX_ANGLE = 130;

// ===== Servo objects =====
Servo horizontalServo;
Servo verticalServo;

// ===== Current angles =====
// הזוויות הנוכחיות של המערכת
int currentHorizontalAngle = 0;
int currentVerticalAngle = 0;

// ===== Initial values =====
const int INITIAL_HORIZONTAL_ANGLE = 0;
const int INITIAL_VERTICAL_ANGLE   = 0;
const int LASER_OFF = LOW;

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

  // הזזת הסרווים למצב התחלתי
  horizontalServo.write(currentHorizontalAngle);
  verticalServo.write(currentVerticalAngle);

  // כיבוי לייזר
  turnLaserOff();
}

/*
  מוודא שהזווית לא חורגת מהטווח החוקי של הסרוו
  אם קטנה מ-0 נחזיר 0
  אם גדולה מ-180 נחזיר 180
*/
int clampAngle(int angle) {
  if (angle < MIN_ANGLE) {
    return MIN_ANGLE;
  }

  if (angle > MAX_ANGLE) {
    return MAX_ANGLE;
  }

  return angle;
}

// מזיז את המנוע האופקי באופן מיידי
void moveHorizontalBy(int deltaAngle) {

  // חישוב זווית יעד חדשה
  int targetAngle = currentHorizontalAngle + deltaAngle;

  // מוודאים שלא חורגים מהמקסימום/מינימום
  targetAngle = clampAngle(targetAngle);

  // הזזה מיידית של הסרוו לזווית החדשה
  horizontalServo.write(targetAngle);

  // עדכון המשתנה הגלובלי לזווית החדשה
  currentHorizontalAngle = targetAngle;
}

// מזיז את המנוע האנכי באופן מיידי
void moveVerticalBy(int deltaAngle) {

  // חישוב זווית יעד
  int targetAngle = currentVerticalAngle + deltaAngle;

  // הגבלת הזווית לטווח חוקי
  targetAngle = clampAngle(targetAngle);

  // הזזת הסרוו
  verticalServo.write(targetAngle);

  // שמירת הזווית החדשה
  currentVerticalAngle = targetAngle;
}

// מזיז את המנוע האופקי בהדרגה, במקום ישירות - בקפיצות של 5 עם דיליי של 100 מילי שניות
void moveHorizontalBySmooth(int deltaAngle) {

  // חישוב זווית היעד
  int targetAngle = currentHorizontalAngle + deltaAngle;

  // מוודאים שלא חורגים מטווח חוקי
  targetAngle = clampAngle(targetAngle);

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
  int targetAngle = currentVerticalAngle + deltaAngle;

  // הגבלת זווית
  targetAngle = clampAngle(targetAngle);

  // ממשיכים עד שמגיעים ליעד
  while (currentVerticalAngle != targetAngle) {

    // אם צריך לעלות בזווית
    if (currentVerticalAngle < targetAngle) {

      currentVerticalAngle += 5;

      // תיקון במקרה שעברנו את היעד
      if (currentVerticalAngle > targetAngle) {
        currentVerticalAngle = targetAngle;
      }

    } else {

      // אם צריך לרדת בזווית
      currentVerticalAngle -= 5;

      // תיקון במקרה שירדנו יותר מדי
      if (currentVerticalAngle < targetAngle) {
        currentVerticalAngle = targetAngle;
      }
    }

    // הזזת המנוע
    verticalServo.write(currentVerticalAngle);

    // המתנה קטנה לתנועה חלקה
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

void resetToHome() {
  currentHorizontalAngle = INITIAL_HORIZONTAL_ANGLE;
  currentVerticalAngle = INITIAL_VERTICAL_ANGLE;
  horizontalServo.write(currentHorizontalAngle);
  verticalServo.write(currentVerticalAngle);
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