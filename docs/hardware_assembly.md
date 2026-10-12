# Hardware Assembly & Wiring Guide

This guide details the physical assembly, pinout wiring, and electrical considerations for the 6-DOF Natural-Language Robot Arm.

---

## 1. Bill of Materials (BOM)

| Component | Part / Model | Qty | Role |
|---|---|---|---|
| Single-Board Computer | Raspberry Pi 5 (8 GB) | 1 | Compute host: ROS 2, CV, LLM |
| 6-DOF Manipulator | LeArm / xArm Lite bracket kit | 1 | Physical arm mechanism |
| Servo Driver | PCA9685 16-channel PWM board | 1 | I²C servo signal generator |
| Actuators | High-torque metal-gear servos (e.g. MG996R, DS3218) | 6 | Joint actuation |
| Camera | Raspberry Pi Camera Module 3 (Wide) | 1 | Bird's-eye workspace perception |
| Microphone | USB MEMS Microphone | 1 | Speech-to-text input |
| Pi Power Supply | 5V / 5A USB-C PD | 1 | Compute node power |
| Servo Power Supply | 6V / 3A-5A DC Barrel Jack | 1 | Dedicated servo power rail |
| Workspace Board | 40 × 40 cm matte white board | 1 | High-contrast CV table |
| Calibration Target | 7 × 7 Checkerboard (25 mm squares) | 1 | Homography calibration |

---

## 2. Power Architecture & Isolation

> [!CAUTION]
> **NEVER power the servos from the Raspberry Pi's 5V GPIO pin!** Simultaneous multi-servo movement draws surge currents exceeding 3.5 Amps, causing instantaneous Pi undervoltage brownouts and file-system corruption.

- **Power Rail 1 (Pi)**: 5V / 5A USB-C Power Delivery directly into the Pi 5.
- **Power Rail 2 (Servos)**: 6V / 3A–5A regulated power supply connected directly into the screw terminal on the PCA9685 board (`V+` and `GND`).
- **Common Ground**: Ensure PCA9685 logic ground (`GND`) is connected to Raspberry Pi GND.

---

## 3. Wiring Diagram: Raspberry Pi 5 ➔ PCA9685

| Raspberry Pi 5 Header Pin | Pi Signal | PCA9685 Header Pin |
|---|---|---|
| Pin 1 | 3.3V Power | `VCC` (Logic Power) |
| Pin 3 | GPIO 2 (SDA) | `SDA` |
| Pin 5 | GPIO 3 (SCL) | `SCL` |
| Pin 9 | Ground | `GND` |

### Servo Channel Connections on PCA9685

Connect servo 3-wire plugs (Signal=Orange/White, V+=Red, GND=Brown/Black) into PCA9685 channels 0 through 5:

- **Channel 0**: Base Yaw (Joint 1)
- **Channel 1**: Shoulder Pitch (Joint 2)
- **Channel 2**: Elbow Pitch (Joint 3)
- **Channel 3**: Wrist Pitch (Joint 4)
- **Channel 4**: Wrist Roll (Joint 5)
- **Channel 5**: Gripper Fingers (Joint 6)

---

## 4. Camera Overhead Mount

1. Mount the **Raspberry Pi Camera Module 3** directly perpendicular to the workspace center at a height of **≈ 40 cm (15.7 inches)**.
2. Aim straight down (90° bird's-eye view).
3. Ensure the full 40 × 40 cm workspace is visible in frame without vignetting.
4. Use diffuse ambient LED lighting or an LED ring light to eliminate harsh specular reflections and deep shadows on the workspace.
