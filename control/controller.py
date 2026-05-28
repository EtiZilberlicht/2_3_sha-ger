from typing import Tuple

import config
from control.aim_geometry import AimGeometry


class TurretController:
    def __init__(self, geometry: AimGeometry | None = None) -> None:
        self.geometry = geometry or AimGeometry()
        self.lock_frame_counter = 0
        self._fire_r2 = config.FIRE_RADIUS_PX * config.FIRE_RADIUS_PX
        self._stable_need = config.STABLE_FRAMES_TO_FIRE
        self._last_fw = 640
        self._last_fh = 480
        self._h_angle = config.SERVO_INIT_H
        self._v_angle = config.SERVO_INIT_V

    @property
    def servo_angles(self) -> Tuple[int, int]:
        return self._h_angle, self._v_angle

    def laser_pixel(self, frame_size: Tuple[int, int]) -> Tuple[int, int]:
        fw, fh = frame_size
        return self.geometry.laser_pixel(self._h_angle, self._v_angle, fw, fh)

    def pixel_error(
        self,
        target: Tuple[int, int],
        frame_size: Tuple[int, int],
    ) -> Tuple[int, int]:
        fw, fh = frame_size
        self._last_fw, self._last_fh = fw, fh
        laser = self.geometry.laser_pixel(self._h_angle, self._v_angle, fw, fh)
        return self.geometry.pixel_error(target, laser)

    @staticmethod
    def _clamp_delta(delta: int, current: int, min_angle: int, max_angle: int) -> int:
        if delta == 0:
            return 0
        target = current + delta
        if target > max_angle:
            return max_angle - current
        if target < min_angle:
            return min_angle - current
        return delta

    @staticmethod
    def _max_cmd_for_err(err: int, base: int, large: int, threshold: int) -> int:
        ae = abs(err)
        if ae >= threshold:
            return large
        if ae >= threshold // 2:
            return (base + large + 1) // 2
        return base

    def _quantize_cmd(self, deg: float, err: int, max_cmd: int, max_large: int) -> int:
        if abs(deg) < 0.01 or abs(err) < config.MIN_MOVE_PX:
            return 0
        cap = max_cmd
        if config.LARGE_ERR_PX and max_large:
            cap = self._max_cmd_for_err(err, max_cmd, max_large, config.LARGE_ERR_PX)
        cmd = int(round(deg))
        if cmd == 0:
            cmd = config.MIN_CMD_DEG if deg > 0 else -config.MIN_CMD_DEG
        return max(-cap, min(cap, cmd))

    def compute_move(self, error_x: int, error_y: int) -> Tuple[int, int]:
        fw, fh = self._last_fw, self._last_fh
        dh, dv = self.geometry.error_to_servo_delta(error_x, error_y, fw, fh)
        h_cmd = self._quantize_cmd(dh, error_x, config.MAX_CMD_DEG, config.MAX_CMD_DEG_LARGE)
        v_cmd = self._quantize_cmd(dv, error_y, config.MAX_CMD_DEG_V, config.MAX_CMD_DEG_V)
        h_cmd = self._clamp_delta(h_cmd, self._h_angle, config.SERVO_H_MIN, config.SERVO_H_MAX)
        v_cmd = self._clamp_delta(v_cmd, self._v_angle, config.SERVO_V_MIN, config.SERVO_V_MAX)
        self._h_angle += h_cmd
        self._v_angle += v_cmd
        return h_cmd, v_cmd

    def reset_home(self) -> None:
        self._h_angle = config.SERVO_INIT_H
        self._v_angle = config.SERVO_INIT_V
        self.lock_frame_counter = 0

    def reset_aim(self) -> None:
        self.lock_frame_counter = 0

    def validate_fire(self, error_x: int, error_y: int) -> bool:
        d2 = error_x * error_x + error_y * error_y
        if d2 <= self._fire_r2:
            self.lock_frame_counter += 1
        else:
            self.lock_frame_counter = 0
        return self.lock_frame_counter >= self._stable_need
