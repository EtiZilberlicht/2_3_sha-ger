from __future__ import annotations

from typing import Optional

import serial


class SerialController:
    def __init__(self) -> None:
        self._ser: Optional[serial.Serial] = None

    def connect(self, port: str, baudrate: int) -> bool:
        try:
            self._ser = serial.Serial(port, baudrate, timeout=0, write_timeout=0)
            return True
        except (OSError, serial.SerialException):
            self._ser = None
            return False

    def send_packet(self, command_type: str, val_x: float, val_y: float) -> None:
        if self._ser is None:
            return
        c = command_type.strip().upper()[:1] or "M"
        self._ser.write(f"{c},{val_x:.4f},{val_y:.4f}\n".encode("ascii", errors="ignore"))

    def send_fire_signal(self, fire: bool) -> None:
        if self._ser is None:
            return
        self._ser.write(("F1\n" if fire else "F0\n").encode("ascii"))
