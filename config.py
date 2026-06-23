PORT = "COM3"
BAUDRATE = 9600
CAMERA_ID = 1
FULLSCREEN = True

YOLO_WEIGHTS = "yolov8n.pt"
YOLO_TRACKER = "bytetrack.yaml"
YOLO_CONF = 0.25
YOLO_CLASSES = [0]

SAM_WEIGHTS = "sam2_t.pt"
ENABLE_SAM = True
SAM_INTERVAL = 8

YOLO_IMGSZ = 640

REID_EMBED_SIZE = 576
REID_UPPER_BODY_RATIO = 0.55
REID_SIM_THRESHOLD = 0.85
REID_REACQUIRE_THRESHOLD = 0.88
REID_ANCHOR_MIN_SIM = 0.82
REID_MATCH_MARGIN = 0.12
REID_LOCK_VERIFY_THRESHOLD = 0.80
REID_LOCK_VERIFY_INTERVAL = 5
REID_LOCK_MISMATCH_MAX = 4
REID_PICK_IOU_MIN = 0.25
REID_GALLERY_MAX = 8
REID_UPDATE_INTERVAL = 15
REID_GALLERY_MIN_DIST = 0.10
REID_GALLERY_MIN_SIM = 0.85
LOST_REID_INTERVAL = 2
REACQUIRE_SPATIAL_BASE_PX = 180
REACQUIRE_SPATIAL_EXPAND_PX = 8

CAM_FOV_DEG_H = 110.0
CAM_FOV_DEG_V = 80.0
H_DEG_TO_PX_SIGN = -1
V_DEG_TO_PX_SIGN = 1
MIN_MOVE_PX = 6
MIN_CMD_DEG = 1
MAX_CMD_DEG = 10
MAX_CMD_DEG_LARGE = 18
LARGE_ERR_PX = 40
MAX_CMD_DEG_V = 8
MOVE_INTERVAL_SEC = 0.12

SERVO_H_MIN = 0
SERVO_H_MAX = 130
SERVO_V_MIN = 0
SERVO_V_MAX = 90
SERVO_INIT_H = 80
SERVO_INIT_V = 20

FIRE_RADIUS_PX = 18
LOCK_ON_TARGET_SEC = 4.0

SMOOTH_ALPHA = 0.35

# Laser home position in pixels (corresponds to the initial servo angles).
# If None, defaults to the center of the frame (320, 240 for a 640x480 resolution).
# Set to shift the predicted laser symbol lower and more to the right to synchronize with the physical laser:
LASER_HOME_X = 150  # Increase to shift right, decrease to shift left
LASER_HOME_Y = 340  # Increase to shift down, decrease to shift up

# cpu | cuda (NVIDIA only) | intel:gpu | intel:cpu | intel:npu
DEVICE = "intel:gpu"

# Servo physical specifications
SERVO_SPEED_DEG_PER_SEC = 400.0  # ~0.15s per 60 degrees

# Parallax coefficients (pixels of shift per pixel of target bounding box height)
# Set to non-zero values to compensate for camera-laser separation
PARALLAX_K_H = 0.0
PARALLAX_K_V = 0.0

