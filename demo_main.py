import time

import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager

DEMO_FIRE_DURATION_SEC = 10.0
DEMO_FIRE_RADIUS_PX = 15
DEMO_APPROACH_RADIUS_PX = 20
DEMO_LOCK_DURATION_SEC = 3.0
DEMO_LOCK_BREAK_SEC = 0.5
DEMO_ERR_SMOOTH_ALPHA = 0.18
FLICKER_HALF_PERIOD_SEC = 0.15


def main():
    serial = SerialController()
    controller = TurretController()
    if serial.connect(config.PORT, config.BAUDRATE):
        print(f"Arduino connected on {config.PORT}")
        serial.startup(controller)
    else:
        print(f"Warning: Arduino not connected on {config.PORT} — running without serial")

    print("Loading vision models...")
    tracker = SentryTracker()
    ui = UIManager()

    if serial.connected:
        serial.homing(controller)
        serial.send_laser_state(True, force=True)
        print("Laser ON — ready to aim")

    cap = cv2.VideoCapture(config.CAMERA_ID, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(config.CAMERA_ID)
    if not cap.isOpened():
        raise RuntimeError(f"Camera {config.CAMERA_ID} not found — change CAMERA_ID in config.py")
    cv2.namedWindow("Sentry AI Turret")
    cv2.setMouseCallback("Sentry AI Turret", ui.mouse_callback, param=tracker)
    frame_i = 0
    last_fire_angles: tuple[int, int] | None = None
    fire_until = 0.0
    last_flicker_at = 0.0
    laser_visible = True
    last_move_at = 0.0
    lock_start: float | None = None
    outside_since: float | None = None
    smooth_err: tuple[float, float] | None = None
    fire_r2 = DEMO_FIRE_RADIUS_PX * DEMO_FIRE_RADIUS_PX
    approach_r2 = DEMO_APPROACH_RADIUS_PX * DEMO_APPROACH_RADIUS_PX
    a = DEMO_ERR_SMOOTH_ALPHA
    last_time = time.time()
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            frame_i += 1
            now = time.time()
            dt = max(0.001, min(0.1, now - last_time))
            last_time = now

            controller.update_actual_angles(dt)

            firing = now < fire_until
            if serial.connected and not firing and frame_i % 120 == 1:
                serial.send_laser_state(True, force=True)

            tracker.update(frame)
            if tracker.consume_aim_reset():
                controller.reset_aim()
                last_fire_angles = None
                lock_start = None
                outside_since = None
                smooth_err = None

            target_center = tracker.get_aim_target()
            fh, fw = frame.shape[:2]
            
            bbox_height = None
            if tracker.status == "LOCKED" and tracker._last_bbox is not None:
                x1, y1, x2, y2 = tracker._last_bbox
                bbox_height = float(y2 - y1)

            aim = controller.laser_pixel((fw, fh), bbox_height)

            move_cmd: tuple[int, int] | None = None
            err: tuple[int, int] | None = None
            if target_center is not None and tracker.status == "LOCKED":
                err_x, err_y = controller.pixel_error(target_center, (fw, fh), bbox_height)
                if smooth_err is None:
                    smooth_err = (float(err_x), float(err_y))
                else:
                    sx, sy = smooth_err
                    smooth_err = (sx * (1 - a) + err_x * a, sy * (1 - a) + err_y * a)
                sx, sy = smooth_err
                err = (int(round(sx)), int(round(sy)))
                near = sx * sx + sy * sy <= approach_r2
                if not firing and not near and now - last_move_at >= config.MOVE_INTERVAL_SEC:
                    h_cmd, v_cmd = controller.compute_move(err_x, err_y)
                    move_cmd = (h_cmd, v_cmd)
                    if h_cmd != 0 or v_cmd != 0:
                        serial.send_move(h_cmd, v_cmd)
                        last_move_at = now
                        lock_start = None
                        outside_since = None
                if not firing:
                    in_zone = sx * sx + sy * sy <= fire_r2
                    if in_zone:
                        outside_since = None
                        if lock_start is None:
                            lock_start = now
                    elif outside_since is None:
                        outside_since = now
                    elif now - outside_since >= DEMO_LOCK_BREAK_SEC:
                        lock_start = None
                    angles = controller.servo_angles
                    moved_since_fire = last_fire_angles is None or angles != last_fire_angles
                    locked_long_enough = (
                        lock_start is not None and now - lock_start >= DEMO_LOCK_DURATION_SEC
                    )
                    if moved_since_fire and locked_long_enough:
                        fire_until = now + DEMO_FIRE_DURATION_SEC
                        last_fire_angles = angles
                        lock_start = None
                        last_flicker_at = now
                        laser_visible = True
                        serial.send_laser_state(True, force=True)
                        print(f"Target locked — firing demo for {DEMO_FIRE_DURATION_SEC:.0f}s")
            else:
                lock_start = None
                outside_since = None
                smooth_err = None
            if firing and serial.connected:
                if now - last_flicker_at >= FLICKER_HALF_PERIOD_SEC:
                    laser_visible = not laser_visible
                    serial.send_laser_state(laser_visible, force=True)
                    last_flicker_at = now
            if fire_until > 0 and now >= fire_until:
                fire_until = 0.0
                lock_start = None
                outside_since = None
                smooth_err = None
                tracker.release_target()
                last_fire_angles = None
                if serial.connected:
                    serial.send_laser_state(True, force=True)
                print("Engagement complete — searching for new target")
            annotated_frame = ui.draw_hud(
                frame,
                tracker.status,
                target_center,
                aim,
                tracker.current_mask,
                move_cmd,
                err,
                controller.servo_angles,
                firing=firing,
            )
            cv2.imshow("Sentry AI Turret", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        print("Shutting down — laser off, turret home...")
        serial.shutdown(controller)
        serial.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
