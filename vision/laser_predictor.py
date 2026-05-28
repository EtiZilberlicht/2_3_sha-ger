from typing import Tuple

from control.aim_geometry import AimGeometry


class LaserPredictor:
    def __init__(self, geometry: AimGeometry | None = None) -> None:
        self.geometry = geometry or AimGeometry()

    def position(
        self,
        servo_angles: Tuple[int, int],
        frame_size: Tuple[int, int],
    ) -> Tuple[int, int]:
        fw, fh = frame_size
        h, v = servo_angles
        return self.geometry.laser_pixel(h, v, fw, fh)
