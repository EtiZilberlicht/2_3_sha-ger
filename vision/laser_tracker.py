from typing import Optional, Tuple

import cv2
import numpy as np


class LaserTracker:
    def __init__(self) -> None:
        # Red hue can wrap around in OpenCV HSV space (0-10 and 160-180)
        # We also look for high saturation and high value (brightness)
        self.lower_red1 = np.array([0, 100, 200])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([160, 100, 200])
        self.upper_red2 = np.array([180, 255, 255])
        self.last_laser_pos: Optional[Tuple[int, int]] = None

    def update(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = mask1 + mask2
        
        # Find contours of the thresholded red areas
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            self.last_laser_pos = None
            return None
            
        # Find the contour with the largest area, likely the laser dot
        c = max(contours, key=cv2.contourArea)
        
        # Calculate the centroid using moments
        M = cv2.moments(c)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            self.last_laser_pos = (cx, cy)
            return (cx, cy)
            
        self.last_laser_pos = None
        return None
