# 🎯 DEADLOCK: Acquire. Track. Lock. Engage.

🏆 **1st Place Winner - Schreiber LevTech Hackathon** 

## 📖 About The Project

**DEADLOCK** is a modular, AI-driven tactical aiming and re-identification (Re-ID) system. Developed as a 3rd-year Computer Science project, it solves one of the most critical challenges in modern warfare: **Target Loss in Complex Environments**. 

Using a continuous tracking camera and an adjustable aiming base, DEADLOCK ensures that a target, once acquired, is never truly lost—even if they temporarily break visual contact.

---

## 📂 Repository Structure & File Overview

Below is the exact technical breakdown of our repository, demonstrating the complete pipeline from AI detection to physical hardware execution:

* `main.py` & `demo_main.py` - **Execution Logic:** The main entry points and execution loops for the system's real-time tracking.
* `config.py` - **System Settings:** Centralized configuration parameters for the camera, models, and hardware limits.
* `control/` - **Aiming & Communication Layer:**
  * `controller.py` - Manages the system's state machine (Searching, Locked, Lost Track, Reacquiring).
  * `aim_geometry.py` - Mathematical module that calculates the physical angles and coordinates required for the sentry base to aim accurately.
  * `serial_sender.py` - Handles the serial communication protocol to send coordinate data to the hardware.
* `arduino/` - **Hardware Firmware:**
  * `sentry/sentry.ino` - The Arduino microcontroller sketch that translates serial commands into physical servo/stepper movements for the adjustable base.
  * `upload.py` - Utility script to easily flash the firmware to the Arduino.
* `sam2_t.pt` - **Cognitive Model:** Pre-trained weights for the Meta SAM 2 (Segment Anything Model 2) used for target signature extraction.
* `requirements.txt` - Python environment dependencies.

---

## 🛠️ Tech Stack & Technologies

DEADLOCK leverages a powerful combination of Edge-AI and hardware:
* **Object Detection & Tracking:** YOLOv8 (Ultralytics) + ByteTrack.
* **Advanced Segmentation:** Meta SAM 2.
* **Hardware Acceleration:** Intel ARC Graphics & OpenVINO Toolkit.
* **Hardware & Actuators:** Arduino.

---

## 📊 Business & Market Validation

DEADLOCK operates under a **B2G / B2B** model with Pay-per-unit hardware integration and Per-Release Pricing for software updates.

### ⚔️ Competitive Advantage
DEADLOCK outperforms existing solutions like Rafael Samson, Dodaam, and SmartShooter by offering a unique combination of **Modular Components**, **Re-Acquisition capabilities**, and an **Accessible Cost**.

--

## 🚀 Getting Started

### Installation
1. **Clone the repository:**
```bash
   git clone [https://github.com/EtiZilberlicht/2_3_sha-ger.git](https://github.com/EtiZilberlicht/2_3_sha-ger.git)

```

2. **Install the required dependencies:**

```bash
   pip install -r requirements.txt

```

3. **Flash the Arduino firmware:**
Located in `arduino/sentry/sentry.ino` (or use `arduino/upload.py`).
4. **Run the system:**

```bash
   python main.py

```

---

## 👩‍💻 The Team (3rd Year Computer Science)

* **Eti Zilberlicht**
* **Talya Haliva**
* **Yael Shneor**
* **Meitav Ben Nun**
* **Yafit Cohen**
* **Shira Ashkenazi**

```
