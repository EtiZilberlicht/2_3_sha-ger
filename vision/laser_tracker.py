from typing import Optional, Tuple

import cv2
import numpy as np

import config


class LaserTracker:
    def __init__(self) -> None:
        self.lower_red1 = np.array([0, 120, 180])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([160, 120, 180])
        self.upper_red2 = np.array([180, 255, 255])
        self._pos: Optional[Tuple[float, float]] = None
        self._last_good: Optional[Tuple[int, int]] = None
        self._lost_frames = 0
        self.calibrated = False

    def _smooth(self, x: int, y: int) -> Tuple[int, int]:
        a = config.LASER_SMOOTH_ALPHA
        if self._pos is None:
            self._pos = (float(x), float(y))
        else:
            self._pos = (a * x + (1.0 - a) * self._pos[0], a * y + (1.0 - a) * self._pos[1])
        return int(round(self._pos[0])), int(round(self._pos[1]))

    def update(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_red1, self.upper_red1) | cv2.inRange(
            hsv, self.lower_red2, self.upper_red2
        )
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best: Optional[Tuple[float, int, int]] = None
        for c in contours:
            area = cv2.contourArea(c)
            if area < config.LASER_MIN_AREA or area > config.LASER_MAX_AREA:
                continue
            M = cv2.moments(c)
            if M["m00"] <= 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if not (0 <= cx < frame.shape[1] and 0 <= cy < frame.shape[0]):
                continue
            v = float(hsv[cy, cx, 2])
            s = float(hsv[cy, cx, 1])
            score = v * 2.0 + s - area * 0.05
            if best is None or score > best[0]:
                best = (score, cx, cy)
        if best is None:
            self._lost_frames += 1
            if self._lost_frames <= config.LASER_HOLD_FRAMES and self._last_good is not None:
                return self._last_good
            return None
        _, cx, cy = best
        pos = self._smooth(cx, cy)
        self._last_good = pos
        self._lost_frames = 0
        self.calibrated = True
        return pos

    def get_aim_point(self) -> Optional[Tuple[int, int]]:
        if self._last_good is not None and self._lost_frames <= config.LASER_HOLD_FRAMES:
            return self._last_good
        return None
