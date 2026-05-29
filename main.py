import time

import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager

FIRE_DURATION_SEC = 3.0

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
    last_move_at = 0.0
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
            if serial.connected and frame_i % 120 == 1:
                serial.send_laser_state(True, force=True)

            tracker.update(frame)
            if tracker.consume_aim_reset():
                controller.reset_aim()
                last_fire_angles = None

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
                err = (err_x, err_y)
                if now - last_move_at >= config.MOVE_INTERVAL_SEC:
                    h_cmd, v_cmd = controller.compute_move(err_x, err_y)
                    move_cmd = (h_cmd, v_cmd)
                    if h_cmd != 0 or v_cmd != 0:
                        serial.send_move(h_cmd, v_cmd)
                        last_move_at = now
                if not firing:
                    angles = controller.servo_angles
                    moved_since_fire = last_fire_angles is None or angles != last_fire_angles
                    if moved_since_fire and controller.validate_fire(err_x, err_y):
                        fire_until = now + FIRE_DURATION_SEC
                        last_fire_angles = angles
                        controller.reset_aim()
                        serial.send_laser_state(True, force=True)
                        print(f"→ Firing for {FIRE_DURATION_SEC:.0f}s")
            else:
                controller.reset_aim()
            if firing and serial.connected:
                serial.send_laser_state(True, force=True)
            annotated_frame = ui.draw_hud(
                frame,
                tracker.status,
                target_center,
                aim,
                tracker.current_mask,
                move_cmd,
                err,
                controller.servo_angles,
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
