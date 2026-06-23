from __future__ import annotations

import time
from typing import Optional, Tuple

import cv2
import numpy as np

from vision.tracker import SentryTracker


class UIManager:
    _THEME = {
        "LOCKED": ((80, 255, 130), (30, 90, 55)),
        "LOST": ((80, 90, 255), (25, 35, 90)),
        "SEARCHING": ((105, 110, 120), (22, 26, 32)),
    }

    def __init__(self, window_name: str = "Sentry AI Turret") -> None:
        self.window_name = window_name
        self._frame_w = 640
        self._frame_h = 480
        self._display_w = 640
        self._display_h = 480

    def set_frame_size(self, w: int, h: int) -> None:
        self._frame_w, self._frame_h = w, h

    @staticmethod
    def screen_size() -> Tuple[int, int]:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
        except Exception:
            return 1920, 1080

    def prepare_display(self, frame: np.ndarray, fullscreen: bool) -> np.ndarray:
        h, w = frame.shape[:2]
        self.set_frame_size(w, h)
        if not fullscreen:
            self.set_display_size(w, h)
            return frame
        sw, sh = self.screen_size()
        display = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_LINEAR)
        self.set_display_size(sw, sh)
        return display

    def set_display_size(self, w: int, h: int) -> None:
        self._display_w, self._display_h = w, h

    def _to_frame_coords(self, x: int, y: int) -> Tuple[int, int]:
        if self._display_w <= 0 or self._display_h <= 0:
            return x, y
        fx = int(round(x * self._frame_w / self._display_w))
        fy = int(round(y * self._frame_h / self._display_h))
        return max(0, min(self._frame_w - 1, fx)), max(0, min(self._frame_h - 1, fy))

    @staticmethod
    def _blend_rect(
        img: np.ndarray, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int], alpha: float
    ) -> None:
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            return
        roi = img[y1:y2, x1:x2].astype(np.float32)
        tint = np.array(color, dtype=np.float32)
        img[y1:y2, x1:x2] = (roi * (1.0 - alpha) + tint * alpha).astype(np.uint8)

    @staticmethod
    def _text(
        img: np.ndarray,
        text: str,
        xy: tuple[int, int],
        scale: float,
        color: tuple[int, int, int],
        thickness: int = 1,
        font=cv2.FONT_HERSHEY_SIMPLEX,
    ) -> tuple[int, int]:
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        cv2.putText(img, text, xy, font, scale, color, thickness, cv2.LINE_AA)
        return tw, th + baseline

    def _status_style(self, status: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return self._THEME.get(status, self._THEME["SEARCHING"])

    def _draw_corners(self, img: np.ndarray, color: tuple[int, int, int], length: int = 28) -> None:
        h, w = img.shape[:2]
        t = 2
        pts = [
            ((0, 0), (length, 0), (0, length)),
            ((w - 1, 0), (w - length - 1, 0), (w - 1, length)),
            ((0, h - 1), (length, h - 1), (0, h - length - 1)),
            ((w - 1, h - 1), (w - length - 1, h - 1), (w - 1, h - length - 1)),
        ]
        for a, b, c in pts:
            cv2.line(img, a, b, color, t, cv2.LINE_AA)
            cv2.line(img, a, c, color, t, cv2.LINE_AA)

    def _draw_crosshair(self, img: np.ndarray, cx: int, cy: int, color: tuple[int, int, int]) -> None:
        gap, arm, r = 7, 18, 14
        cv2.circle(img, (cx, cy), r, color, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 2, color, -1, cv2.LINE_AA)
        cv2.line(img, (cx - arm, cy), (cx - gap, cy), color, 1, cv2.LINE_AA)
        cv2.line(img, (cx + gap, cy), (cx + arm, cy), color, 1, cv2.LINE_AA)
        cv2.line(img, (cx, cy - arm), (cx, cy - gap), color, 1, cv2.LINE_AA)
        cv2.line(img, (cx, cy + gap), (cx, cy + arm), color, 1, cv2.LINE_AA)

    def _draw_target(self, img: np.ndarray, cx: int, cy: int, color: tuple[int, int, int]) -> None:
        cv2.circle(img, (cx, cy), 22, color, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 12, color, 1, cv2.LINE_AA)
        cv2.drawMarker(img, (cx, cy), color, cv2.MARKER_CROSS, 16, 1, cv2.LINE_AA)

    def _draw_dashed_line(
        self, img: np.ndarray, p1: tuple[int, int], p2: tuple[int, int], color: tuple[int, int, int]
    ) -> None:
        x1, y1 = p1
        x2, y2 = p2
        dist = int(np.hypot(x2 - x1, y2 - y1))
        if dist == 0:
            return
        dash, gap = 10, 7
        for i in range(0, dist, dash + gap):
            t0, t1 = i / dist, min(i + dash, dist) / dist
            ax, ay = int(x1 + (x2 - x1) * t0), int(y1 + (y2 - y1) * t0)
            bx, by = int(x1 + (x2 - x1) * t1), int(y1 + (y2 - y1) * t1)
            cv2.line(img, (ax, ay), (bx, by), color, 1, cv2.LINE_AA)

    def _draw_top_bar(
        self, img: np.ndarray, status: str, target_center: Optional[Tuple[int, int]], firing: bool = False
    ) -> None:
        accent, panel = self._status_style(status)
        if firing:
            pulse = 0.85 + 0.15 * np.sin(time.time() * 15.0)
            accent = (int(50 * pulse), int(50 * pulse), int(255 * pulse))
            panel = (20, 20, 75)
        self._blend_rect(img, 0, 0, img.shape[1], 56, panel, 0.72)
        cv2.line(img, (0, 56), (img.shape[1], 56), accent, 2, cv2.LINE_AA)
        sub = (
            "TARGET ACQUIRED"
            if status == "LOCKED"
            else "REACQUIRING..."
            if status == "LOST"
            else ""
        )
        gray = (105, 110, 120)
        if status == "SEARCHING":
            self._text(img, "SEARCHING", (18, 30), 0.85, gray, 2)
            self._text(img, "Click to lock target", (18, 50), 0.48, gray, 1)
        else:
            display_status = "FIRING" if firing else status
            self._text(img, display_status, (18, 38), 0.95, accent, 2)
            if firing:
                self._text(img, "ACTIVE ENGAGEMENT", (160, 38), 0.52, (180, 180, 255), 1)
            elif sub:
                self._text(img, sub, (160, 38), 0.52, (235, 238, 245), 1)
        self._text(img, "SENTRY AI", (img.shape[1] - 130, 28), 0.55, (210, 215, 225), 1)
        self._text(img, "LASER · MATH", (img.shape[1] - 130, 48), 0.45, gray if status == "SEARCHING" else accent, 1)
        if target_center is not None:
            tx, ty = target_center
            coord = f"({tx}, {ty})"
            tw, _ = cv2.getTextSize(coord, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
            self._text(img, coord, (img.shape[1] - tw - 18, 38), 0.45, (220, 225, 235), 1)

    def _draw_bottom_bar(
        self,
        img: np.ndarray,
        err: Optional[Tuple[int, int]],
        move_cmd: Optional[Tuple[int, int]],
        servo_angles: Optional[Tuple[int, int]],
    ) -> None:
        h, w = img.shape[:2]
        bar_h = 52
        y0 = h - bar_h
        self._blend_rect(img, 0, y0, w, h, (38, 40, 48), 0.78)
        cv2.line(img, (0, y0), (w, y0), (90, 95, 110), 1, cv2.LINE_AA)
        cols = [(18, "ERROR"), (w // 3 + 8, "MOVE"), (2 * w // 3 + 4, "SERVO")]
        for x, title in cols:
            self._text(img, title, (x, y0 + 18), 0.42, (175, 180, 190), 1)
        if err is not None:
            self._text(img, f"{err[0]:+d}px  {err[1]:+d}px", (18, y0 + 42), 0.58, (100, 220, 255), 1)
        else:
            self._text(img, "—", (18, y0 + 42), 0.58, (175, 180, 190), 1)
        if move_cmd is not None:
            self._text(img, f"H {move_cmd[0]:+d}   V {move_cmd[1]:+d}", (w // 3 + 8, y0 + 42), 0.58, (120, 255, 220), 1)
        else:
            self._text(img, "—", (w // 3 + 8, y0 + 42), 0.58, (175, 180, 190), 1)
        if servo_angles is not None:
            sh, sv = servo_angles
            self._text(
                img,
                f"H {sh}°   V {sv}°",
                (2 * w // 3 + 4, y0 + 42),
                0.58,
                (210, 210, 220),
                1,
            )
        else:
            self._text(img, "—", (2 * w // 3 + 4, y0 + 42), 0.58, (175, 180, 190), 1)

    def draw_hud(
        self,
        frame: np.ndarray,
        status: str,
        target_center: Optional[Tuple[int, int]],
        aim_point: Optional[Tuple[int, int]],
        mask: Optional[np.ndarray],
        move_cmd: Optional[Tuple[int, int]] = None,
        err: Optional[Tuple[int, int]] = None,
        servo_angles: Optional[Tuple[int, int]] = None,
        firing: bool = False,
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        accent, _ = self._status_style(status)

        if firing:
            pulse = 0.85 + 0.15 * np.sin(time.time() * 15.0)
            accent = (int(50 * pulse), int(50 * pulse), int(255 * pulse))

        if mask is not None and mask.shape[0] == h and mask.shape[1] == w:
            tint = np.zeros_like(out)
            tint[:, :] = (70, 210, 120)
            alpha = (mask.astype(np.float32) / 255.0)[..., None] * 0.35
            out = (out.astype(np.float32) * (1.0 - alpha) + tint.astype(np.float32) * alpha).astype(np.uint8)

        if aim_point is not None:
            lx, ly = aim_point
            self._draw_crosshair(out, lx, ly, (70, 70, 255))
            if target_center is not None:
                self._draw_dashed_line(out, (lx, ly), target_center, (80, 160, 255))

        if target_center is not None:
            self._draw_target(out, target_center[0], target_center[1], accent)

        self._draw_corners(out, accent)
        self._draw_top_bar(out, status, target_center, firing=firing)
        self._draw_bottom_bar(out, err, move_cmd, servo_angles)

        if firing:
            # Pulsing neon red border around the whole video feed
            cv2.rectangle(out, (0, 0), (w - 1, h - 1), accent, 4)
            
            # Blinking center-top alert badge
            blink = int(time.time() * 4) % 2 == 0
            if blink:
                warn_text = "WARNING: SHOOTING"
                scale = 0.50
                thickness = 1
                (tw, th), baseline = cv2.getTextSize(warn_text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
                bx = w // 2 - tw // 2
                by = 85
                pad_x, pad_y = 12, 6
                self._blend_rect(out, bx - pad_x, by - th - pad_y, bx + tw + pad_x, by + pad_y, (15, 15, 75), 0.8)
                cv2.rectangle(out, (bx - pad_x, by - th - pad_y), (bx + tw + pad_x, by + pad_y), accent, 1, cv2.LINE_AA)
                self._text(out, warn_text, (bx, by - 2), scale, (200, 200, 255), thickness)

        return out

    def mouse_callback(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        tracker = param
        if not isinstance(tracker, SentryTracker) or tracker.last_frame is None:
            return
        fx, fy = self._to_frame_coords(x, y)
        tracker.set_target_from_click(tracker.last_frame, fx, fy)

