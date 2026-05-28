from typing import Tuple

import config


class TurretController:
    def __init__(self) -> None:
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

    def calculate_pixel_error(
        self,
        target_center: Tuple[int, int],
        ref_center: Tuple[int, int],
        frame_size: Tuple[int, int],
    ) -> Tuple[int, int]:
        fw, fh = frame_size
        self._last_fw, self._last_fh = fw, fh
        tx, ty = target_center
        rx, ry = ref_center
        return int(tx - rx), int(ty - ry)

    @staticmethod
    def _clamp_delta(delta: int, current: int) -> int:
        if delta == 0:
            return 0
        target = current + delta
        if target > config.SERVO_MAX_ANGLE:
            return config.SERVO_MAX_ANGLE - current
        if target < config.SERVO_MIN_ANGLE:
            return config.SERVO_MIN_ANGLE - current
        return delta

    def _axis_cmd(self, err: int, span: float, fov: float, sign: int, current: int) -> int:
        if abs(err) < config.MIN_MOVE_PX:
            return 0
        deg = err / max(1.0, span) * fov * config.ANGLE_CMD_SCALE * sign
        cmd = int(round(deg))
        if cmd == 0:
            cmd = config.MIN_CMD_DEG if deg > 0 else -config.MIN_CMD_DEG
        cmd = max(-config.MAX_CMD_DEG, min(config.MAX_CMD_DEG, cmd))
        return self._clamp_delta(cmd, current)

    def compute_move(self, error_x: int, error_y: int) -> Tuple[int, int]:
        w = max(1.0, float(self._last_fw))
        h = max(1.0, float(self._last_fh))
        dx = self._axis_cmd(error_x, w, config.FOV_DEG_H, config.H_SIGN, self._h_angle)
        dy = self._axis_cmd(error_y, h, config.FOV_DEG_V, config.V_SIGN, self._v_angle)
        self._h_angle += dx
        self._v_angle += dy
        return dx, dy

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
