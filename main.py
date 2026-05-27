from __future__ import annotations

import cv2

import config
from control.controller import TurretController
from control.serial_sender import SerialController
from vision.tracker import SentryTracker
from vision.ui_manager import UIManager


def main() -> None:
    tracker = SentryTracker()
    ui = UIManager()
    controller = TurretController()
    serial = SerialController()
    if config.ENABLE_SERIAL:
        serial.connect(config.PORT, config.BAUDRATE)
    cap = cv2.VideoCapture(config.CAMERA_ID)
    cv2.namedWindow(ui.window_name)
    cv2.setMouseCallback(ui.window_name, ui.mouse_callback, param=tracker)
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
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
            controller.reset_lock()
            serial.send_fire_signal(False)
        annotated = ui.draw_hud(
            frame, tracker.status, target_center, tracker.current_mask, tracker.last_boxes
        )
        cv2.imshow(ui.window_name, annotated)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
