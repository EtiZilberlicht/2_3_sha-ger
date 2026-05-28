from typing import Tuple

import config


class TurretController:
    def __init__(self) -> None:
        self.lock_frame_counter = 0
        self._sx = 0.0
        self._sy = 0.0
        self._fire_r2 = config.FIRE_RADIUS_PX * config.FIRE_RADIUS_PX
        self._stable_need = config.STABLE_FRAMES_TO_FIRE
        self._last_fw = 640
        self._last_fh = 480

    def calculate_pixel_error(
        self, target_center: Tuple[int, int], frame_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        fw, fh = frame_size
        self._last_fw, self._last_fh = fw, fh
        cx, cy = fw // 2, fh // 2
        tx, ty = target_center
        return int(tx - cx), int(ty - cy)

    def convert_to_angles(self, error_x: int, error_y: int) -> Tuple[float, float]:
        w = max(1.0, float(self._last_fw))
        h = max(1.0, float(self._last_fh))
        return (
            float(error_x) / w * config.FOV_DEG_H * config.ANGLE_CMD_SCALE,
            float(error_y) / h * config.FOV_DEG_V * config.ANGLE_CMD_SCALE,
        )

    def filter_smoothing(self, delta_x: float, delta_y: float) -> Tuple[float, float]:
        a = config.SMOOTH_ALPHA
        self._sx = a * delta_x + (1.0 - a) * self._sx
        self._sy = a * delta_y + (1.0 - a) * self._sy
        return self._sx, self._sy

    def validate_fire(self, error_x: int, error_y: int) -> bool:
        d2 = error_x * error_x + error_y * error_y
        if d2 <= self._fire_r2:
            self.lock_frame_counter += 1
        else:
            self.lock_frame_counter = 0
        return self.lock_frame_counter >= self._stable_need
