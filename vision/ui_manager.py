def start_live_stream(camera_id: int) -> None:
    print(f"Starting live stream for camera {camera_id}...")

def select_target_callback(event, x, y, flags, param) -> Box:
    print(f"Mouse event: {event}, Position: ({x}, {y}), Flags: {flags}")