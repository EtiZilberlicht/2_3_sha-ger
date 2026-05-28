import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager


def main():
    tracker = SentryTracker()
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
        if target_center is not None:
            err_x, err_y = controller.calculate_pixel_error(
                target_center, (frame.shape[1], frame.shape[0])
            )
            delta_x, delta_y = controller.convert_to_angles(err_x, err_y)
            smooth_x, smooth_y = controller.filter_smoothing(delta_x, delta_y)
            serial.send_packet("M", smooth_x, smooth_y)
            if controller.validate_fire(err_x, err_y):
                serial.send_fire_signal(True)
            else:
                serial.send_fire_signal(False)
        else:
            serial.send_fire_signal(False)
        annotated_frame = ui.draw_hud(frame, tracker.status, target_center, tracker.current_mask)
        cv2.imshow("Sentry AI Turret", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
