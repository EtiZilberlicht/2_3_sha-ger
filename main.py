import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager
from vision.laser_tracker import LaserTracker


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
    laser_tracker = LaserTracker()
    ui = UIManager()

    if serial.connected:
        serial.homing(controller, from_tracked=False)
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
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            frame_i += 1
            if serial.connected and frame_i % 120 == 1:
                serial.send_laser_state(True, force=True)

            tracker.update(frame)
            if tracker.consume_aim_reset():
                controller.reset_aim()

            target_center = tracker.get_aim_target()
            laser_center = laser_tracker.update(frame)
            aim = laser_tracker.get_aim_point()

            move_cmd: tuple[int, int] | None = None
            err: tuple[int, int] | None = None
            if target_center is not None and aim is not None:
                fh, fw = frame.shape[:2]
                err_x, err_y = controller.calculate_pixel_error(target_center, aim, (fw, fh))
                err = (err_x, err_y)
                dx, dy = controller.compute_move(err_x, err_y)
                move_cmd = (dx, dy)
                if dx != 0 or dy != 0:
                    serial.send_move(dx, dy)
                if controller.validate_fire(err_x, err_y):
                    serial.send_fire()

            annotated_frame = ui.draw_hud(
                frame,
                tracker.status,
                target_center,
                laser_center,
                aim,
                tracker.current_mask,
                move_cmd,
                err,
                controller.servo_angles if target_center is not None and aim is not None else None,
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
