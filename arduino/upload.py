import os
import sys
import subprocess
import argparse
import time

'''
python upload.py

python upload.py --port COM3 --fqbn arduino:avr:uno

python upload.py --monitor
'''




def find_arduino_cli():
    # 1. Check if in PATH
    try:
        subprocess.run(["arduino-cli", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "arduino-cli"
    except FileNotFoundError:
        pass

    # 2. Check standard Arduino IDE 2.x location in Local AppData
    user_home = os.path.expanduser("~")
    local_path = os.path.join(
        user_home, 
        "AppData", "Local", "Programs", "Arduino IDE", 
        "resources", "app", "lib", "backend", "resources", "arduino-cli.exe"
    )
    if os.path.exists(local_path):
        return local_path

    # 3. Fallback standard Arduino IDE 2.x location (Program Files)
    program_files_path = os.path.join(
        "C:\\Program Files\\Arduino IDE", 
        "resources", "app", "lib", "backend", "resources", "arduino-cli.exe"
    )
    if os.path.exists(program_files_path):
        return program_files_path

    return None

def get_connected_board_port(cli_path):
    print("Scanning for connected Arduino boards...")
    try:
        result = subprocess.run([cli_path, "board", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        
        # Look for a COM port that has a board detected
        # Header is usually: Port Protocol Type Board Name FQBN Core
        # Example line: COM3 serial Serial Port Arduino Uno arduino:avr:uno arduino:avr
        for line in lines[1:]: # Skip header
            parts = line.split()
            if len(parts) >= 2:
                port = parts[0]
                if port.startswith("COM"):
                    fqbn = None
                    for part in parts:
                        if ":" in part and len(part.split(":")) == 3:
                            fqbn = part
                            break
                    return port, fqbn
    except Exception as e:
        print(f"Error listing boards: {e}")
    return None, None

def run_command(command):
    print(f"Running command: {' '.join(command)}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    # Read output line by line as it is generated
    for line in process.stdout:
        print(line, end="")
        
    process.wait()
    return process.returncode

def main():
    parser = argparse.ArgumentParser(description="Compile and upload Arduino sketch.")
    parser.add_argument("--port", help="COM port of the Arduino (e.g. COM3). Auto-detected if omitted.")
    parser.add_argument("--fqbn", default="arduino:avr:uno", help="Fully Qualified Board Name (default: arduino:avr:uno).")
    parser.add_argument("--sketch", default="sentry", help="Folder containing the .ino file (default: sentry).")
    parser.add_argument("--monitor", action="store_true", help="Start serial monitor after successful upload.")
    args = parser.parse_args()

    # Find arduino-cli
    cli_path = find_arduino_cli()
    if not cli_path:
        print("Error: Could not find arduino-cli.exe. Please ensure Arduino IDE is installed.")
        sys.exit(1)
    print(f"Found arduino-cli at: {cli_path}")

    # Determine sketch path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sketch_path = os.path.join(script_dir, args.sketch)
    if not os.path.exists(sketch_path):
        print(f"Error: Sketch path '{sketch_path}' does not exist.")
        sys.exit(1)

    # Compile sketch
    print("\n=== Compiling Sketch ===")
    compile_cmd = [cli_path, "compile", "--fqbn", args.fqbn, sketch_path]
    rc = run_command(compile_cmd)
    if rc != 0:
        print("Compilation failed!")
        sys.exit(rc)
    print("Compilation successful.")

    # Detect COM Port and FQBN if not provided
    port = args.port
    fqbn = args.fqbn
    if not port:
        detected_port, detected_fqbn = get_connected_board_port(cli_path)
        if detected_port:
            port = detected_port
            print(f"Auto-detected board on port: {port}")
            if detected_fqbn:
                fqbn = detected_fqbn
                print(f"Auto-detected FQBN: {fqbn}")
        else:
            print("\nError: No Arduino board auto-detected.")
            print("Please plug in your Arduino, or specify the port manually using --port (e.g. --port COM3).")
            print("Available port scan:")
            subprocess.run([cli_path, "board", "list"])
            sys.exit(1)

    # Upload sketch
    print(f"\n=== Uploading Sketch to {port} ===")
    upload_cmd = [cli_path, "upload", "-p", port, "--fqbn", fqbn, sketch_path]
    rc = run_command(upload_cmd)
    if rc != 0:
        print("Upload failed!")
        sys.exit(rc)
    print("Upload successful!")

    # Start serial monitor if requested
    if args.monitor:
        print(f"\n=== Starting Serial Monitor on {port} (Ctrl+C to exit) ===")
        time.sleep(1) # Wait for reset
        monitor_cmd = [cli_path, "monitor", "-p", port, "-c", "baudrate=9600"]
        try:
            run_command(monitor_cmd)
        except KeyboardInterrupt:
            print("\nSerial Monitor stopped.")

if __name__ == "__main__":
    main()


