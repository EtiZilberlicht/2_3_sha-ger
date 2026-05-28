import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager
from vision.laser_tracker import LaserTracker


def main():
    tracker = SentryTracker()
    laser_tracker = LaserTracker()
    ui = UIManager()
    controller = TurretController()
    serial = SerialController()
    serial.connect(config.PORT, config.BAUDRATE)
    cap = cv2.VideoCapture(config.CAMERA_ID, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(config.CAMERA_ID)
    if not cap.isOpened():
        raise RuntimeError(f"Camera {config.CAMERA_ID} not found — change CAMERA_ID in config.py")
    cv2.namedWindow("Sentry AI Turret")
    cv2.setMouseCallback("Sentry AI Turret", ui.mouse_callback, param=tracker)
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        target_center = tracker.update(frame)
        laser_center = laser_tracker.update(frame)
        
        serial.send_laser_state(target_center is not None)
        
        if target_center is not None and laser_center is not None:
            err_x, err_y = controller.calculate_pixel_error(
                target_center, laser_center, (frame.shape[1], frame.shape[0])
            )
            delta_x, delta_y = controller.convert_to_angles(err_x, err_y)
            smooth_x, smooth_y = controller.filter_smoothing(delta_x, delta_y)
            serial.send_move(round(smooth_x), round(smooth_y))
            if controller.validate_fire(err_x, err_y):
                serial.send_fire()
        
        annotated_frame = ui.draw_hud(frame, tracker.status, target_center, laser_center, tracker.current_mask)
        cv2.imshow("Sentry AI Turret", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
