#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <Servo.h>

Servo servoX;
Servo servoY;

const uint8_t PIN_SERVO_X = 9;
const uint8_t PIN_SERVO_Y = 10;
const uint8_t PIN_LASER = 7;

char lineBuf[96];
uint8_t lineLen = 0;

float angleX = 90.0f;
float angleY = 90.0f;

void applyDelta(float dx, float dy) {
  angleX += dx;
  angleY += dy;
  if (angleX < 0.0f) angleX = 0.0f;
  if (angleX > 180.0f) angleX = 180.0f;
  if (angleY < 0.0f) angleY = 0.0f;
  if (angleY > 180.0f) angleY = 180.0f;
  servoX.write((int)(angleX + 0.5f));
  servoY.write((int)(angleY + 0.5f));
}

void handleLine(char *line) {
  while (*line && isspace((unsigned char)*line)) line++;
  if (!*line) return;
  char c = (char)toupper((unsigned char)*line);
  if (c == 'F') {
    int v = atoi(line + 1);
    digitalWrite(PIN_LASER, v ? HIGH : LOW);
    return;
  }
  if (c == 'M' && line[1] == ',') {
    float dx, dy;
    if (sscanf(line + 2, "%f,%f", &dx, &dy) == 2) applyDelta(dx, dy);
  }
}

void setup() {
  Serial.begin(9600);
  servoX.attach(PIN_SERVO_X);
  servoY.attach(PIN_SERVO_Y);
  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_LASER, LOW);
  servoX.write((int)(angleX + 0.5f));
  servoY.write((int)(angleY + 0.5f));
}

void loop() {
  while (Serial.available() > 0) {
    int r = Serial.read();
    if (r < 0) break;
    char ch = (char)r;
    if (ch == '\r') continue;
    if (ch == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
      continue;
    }
    if (lineLen >= sizeof(lineBuf) - 1) {
      lineLen = 0;
      continue;
    }
    lineBuf[lineLen++] = ch;
  }
}
