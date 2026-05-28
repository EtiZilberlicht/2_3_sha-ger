from typing import Tuple

import config


class AimGeometry:
    def home_px(self, fw: int, fh: int) -> Tuple[int, int]:
        x = config.LASER_HOME_X if config.LASER_HOME_X is not None else fw // 2
        y = config.LASER_HOME_Y if config.LASER_HOME_Y is not None else fh // 2
        return x, y

    def px_per_deg_h(self, fw: int) -> float:
        return fw / config.CAM_FOV_DEG_H * config.H_DEG_TO_PX_SIGN

    def px_per_deg_v(self, fh: int) -> float:
        return fh / config.CAM_FOV_DEG_V * config.V_DEG_TO_PX_SIGN

    def laser_pixel(self, servo_h: int, servo_v: int, fw: int, fh: int) -> Tuple[int, int]:
        hx, hy = self.home_px(fw, fh)
        dh = servo_h - config.SERVO_INIT_H
        dv = servo_v - config.SERVO_INIT_V
        lx = int(round(hx + dh * self.px_per_deg_h(fw)))
        ly = int(round(hy + dv * self.px_per_deg_v(fh)))
        return max(0, min(fw - 1, lx)), max(0, min(fh - 1, ly))

    def pixel_error(
        self,
        target: Tuple[int, int],
        laser: Tuple[int, int],
    ) -> Tuple[int, int]:
        return int(target[0] - laser[0]), int(target[1] - laser[1])

    def error_to_servo_delta(self, err_x: int, err_y: int, fw: int, fh: int) -> Tuple[float, float]:
        dh = err_x / self.px_per_deg_h(fw)
        dv = 0.0
        if err_y > 0:
            dv = err_y / self.px_per_deg_v(fh)
        elif err_y < 0:
            dh += err_y / self.px_per_deg_v(fh)
        return dh, dv
