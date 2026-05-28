import time

import serial

import config


class SerialController:
    def __init__(self) -> None:
        self._ser = None
        self._laser_on = False
        self.connected = False

    def connect(self, port: str, baudrate: int) -> bool:
        try:
            self._ser = serial.Serial(port, baudrate, timeout=0, write_timeout=1)
            time.sleep(2.5)
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self.connected = True
            return True
        except (OSError, serial.SerialException) as e:
            self._ser = None
            self.connected = False
            print(f"Serial connect failed ({port}): {e}")
            return False

    def _write(self, cmd: str) -> None:
        if self._ser is None:
            return
        self._ser.write(cmd.encode("ascii"))
        self._ser.flush()

    def send_move(self, delta_h: int, delta_v: int) -> None:
        if self._ser is None:
            return
        if delta_h != 0:
            self._write(f"H {delta_h}\n")
        if delta_v != 0:
            self._write(f"V {delta_v}\n")
        if delta_h != 0 or delta_v != 0:
            print(f"→ Arduino: H {delta_h}  V {delta_v}")

    def send_goto(self, h: int, v: int) -> None:
        if self._ser is None:
            return
        self._write(f"G {h} {v}\n")
        print(f"→ Arduino: G {h} {v}")

    def send_reset(self) -> None:
        if self._ser is None:
            return
        self._write("RESET\n")
        print("→ Arduino: RESET")

    def send_laser_state(self, on: bool, force: bool = False) -> None:
        if self._ser is None:
            return
        if not force and on == self._laser_on:
            return
        self._laser_on = on
        cmd = "LASER_ON\n" if on else "LASER_OFF\n"
        self._write(cmd)
        print(f"→ Arduino: {cmd.strip()}")

    def send_fire(self) -> None:
        if self._ser is None:
            return
        self._write("FIRE\n")

    def homing(self, controller=None) -> None:
        if self._ser is None:
            return
        ih, iv = config.SERVO_INIT_H, config.SERVO_INIT_V
        self.send_goto(ih, iv)
        time.sleep(0.6)
        if controller is not None:
            controller.reset_home()

    def startup(self, controller) -> None:
        if self._ser is None:
            return
        print("Homing turret to start position...")
        self.send_laser_state(False, force=True)
        time.sleep(0.2)
        self.homing(controller)

    def shutdown(self, controller=None) -> None:
        if self._ser is None:
            return
        self.send_laser_state(False, force=True)
        time.sleep(0.2)
        self.homing(controller)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None
        self.connected = False
