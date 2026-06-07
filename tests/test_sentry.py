import time
import serial

PORT = "COM3"        # Change based on the Arduino port
BAUD_RATE = 9600

def send_command(ser, command):
    print(f"Sending: {command}")
    ser.write((command + "\n").encode())
    time.sleep(1)


def main():
    with serial.Serial(PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)  # Allow time for the Arduino to reset

        # print("=== Test 1: Fire laser ===")
        # send_command(ser, "FIRE")

        # print("=== Test 2: Laser on/off ===")
        # send_command(ser, "LASER_ON")
        # send_command(ser, "LASER_OFF")

        print("=== Test 3: Horizontal movement ===")
        send_command(ser, "H 0")

        print("=== Test 4: Vertical movement ===")
        send_command(ser, "V -45")

        # print("=== Test 5: Smooth horizontal movement ===")
        # send_command(ser, "HS 40")
        # send_command(ser, "HS -40")

        # print("=== Test 6: Smooth vertical movement ===")
        # send_command(ser, "VS 40")
        # send_command(ser, "VS -40")

        # print("=== Test 7: Angle limits ===")
        # send_command(ser, "H 999")
        # send_command(ser, "H -999")
        # send_command(ser, "V 999")
        # send_command(ser, "V -999")

        print("All tests sent.")


if __name__ == "__main__":
    main()
