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
        mask: Optional[np.ndarray],
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.line(out, (cx - 24, cy), (cx + 24, cy), (0, 255, 255), 1, cv2.LINE_AA)
        cv2.line(out, (cx, cy - 24), (cx, cy + 24), (0, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(out, (cx, cy), 10, (0, 255, 255), 1, cv2.LINE_AA)
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
        if target_center is not None:
            tx, ty = target_center
            cv2.circle(out, (tx, ty), 6, color, -1, cv2.LINE_AA)
            label = f"{status} ({tx},{ty})"
        cv2.putText(out, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        return out

    def mouse_callback(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        tracker = param
        if not isinstance(tracker, SentryTracker) or tracker.last_frame is None:
            return
        tracker.set_target_from_click(tracker.last_frame, x, y)
