from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np

from vision.tracker import SentryTracker


class UIManager:
    def __init__(self, window_name: str = "Sentry AI Turret") -> None:
        self.window_name = window_name

    def draw_hud(
        self,
        frame: np.ndarray,
        status: str,
        target_center: Optional[Tuple[int, int]],
        laser_center: Optional[Tuple[int, int]],
        aim_point: Optional[Tuple[int, int]],
        mask: Optional[np.ndarray],
        move_cmd: Optional[Tuple[int, int]] = None,
        err: Optional[Tuple[int, int]] = None,
        servo_angles: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        if aim_point is not None:
            lx, ly = aim_point
            cv2.circle(out, (lx, ly), 10, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.circle(out, (lx, ly), 3, (0, 0, 255), -1, cv2.LINE_AA)
            if target_center is not None:
                cv2.line(out, (lx, ly), target_center, (255, 100, 0), 1, cv2.LINE_AA)
        elif laser_center is not None:
            lx, ly = laser_center
            cv2.circle(out, (lx, ly), 8, (0, 0, 255), 2, cv2.LINE_AA)
        if mask is not None and mask.shape[0] == h and mask.shape[1] == w:
            col = np.zeros_like(out)
            col[:, :] = (0, 200, 0)
            alpha = mask.astype(np.float32) / 255.0
            a = np.clip(alpha[..., None], 0.0, 1.0)
            out = (out.astype(np.float32) * (1.0 - 0.45 * a) + col.astype(np.float32) * (0.45 * a)).astype(
                np.uint8
            )
        if status == "LOCKED":
            color = (0, 220, 0)
        elif status == "LOST":
            color = (0, 0, 255)
        else:
            color = (200, 200, 200)
        label = status
        if aim_point is None:
            label = f"{status} | LASER: searching..."
        else:
            label = f"{status} | LASER: locked"
        if target_center is not None:
            tx, ty = target_center
            cv2.circle(out, (tx, ty), 6, color, -1, cv2.LINE_AA)
            label = f"{status} ({tx},{ty})"
        if err is not None:
            cv2.putText(
                out,
                f"ERR px={err[0]},{err[1]}",
                (12, 58),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 200, 0),
                1,
                cv2.LINE_AA,
            )
        if move_cmd is not None:
            cv2.putText(
                out,
                f"MOVE H={move_cmd[0]} V={move_cmd[1]}",
                (12, h - 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 0),
                2,
                cv2.LINE_AA,
            )
        if servo_angles is not None:
            cv2.putText(
                out,
                f"ANGLE H={servo_angles[0]} V={servo_angles[1]} (0-130)",
                (12, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )
        cv2.putText(out, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        return out

    def mouse_callback(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        tracker = param
        if not isinstance(tracker, SentryTracker) or tracker.last_frame is None:
            return
        tracker.set_target_from_click(tracker.last_frame, x, y)
