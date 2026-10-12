# Natural-Language-Controlled 6-DOF Robot Arm

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![ROS 2: Humble](https://img.shields.io/badge/ROS%202-Humble-orange.svg)](https://docs.ros.org/en/humble/)
[![Tests: 100% Passed](https://img.shields.io/badge/Tests-15%2F15%20Passed-emerald.svg)](tests/)

> **Tell the arm:** *"Pick up the red block, place it on the blue mat"* — it perceives the workspace, decomposes the instruction into atomic steps, calculates inverse kinematics, and executes multi-step pick-and-place trajectories autonomously.

---

## 🌟 Overview

This repository provides a complete **Vision-Language-Action (VLA)** robotic manipulation system designed for embedded deployment on a **Raspberry Pi 5** with a **6-DOF servo arm**, while maintaining 100% testability on any computer via standalone simulation and an interactive Web Dashboard.

```
┌─────────────────────────────────────────────────────────────┐
│                    NATURAL LANGUAGE INPUT                   │
│         "Pick up the red block, place it on blue mat"       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               LLM TASK PLANNER (Phi-3 / Rule Engine)        │
│  Outputs structured atomic action sequence:                 │
│  [{"action": "pick", "object_name": "red_block"},           │
│   {"action": "place", "target_name": "blue_mat"}]           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              PERCEPTION (OpenCV HSV / YOLOv8-nano)          │
│  Bird's-eye camera frame -> Homography (pixels to mm)       │
│  red_block -> (-50.2, 140.0, 15.0) mm                       │
│  blue_mat  -> ( 58.6, 181.2, 20.0) mm                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             MOTION PLANNING (Analytical IK + S-Curve)       │
│  Computes 6-DOF joint angles & minimum-jerk trajectory      │
│  Enforces workspace limits & top-down approach              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          ACTUATION (PCA9685 I²C Driver / Simulator)         │
│  Smooth 50ms servo pulse execution: approach->grasp->place  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

- **Dual-Mode System**: Runs natively as a compiled **ROS 2 Humble** node network on Raspberry Pi 5 / Linux, OR as a **zero-dependency Standalone Simulator** on Windows/macOS.
- **Natural Language Task Decomposition**: Quantized on-device LLM (`phi-3-mini-4k-instruct.Q4_K_M.gguf`) with deterministic heuristic rule-based parser fallback.
- **Overhead Computer Vision**: HSV color segmentation with dual-range wrap handling, contour classification, checkerboard homography transform (`calibrate.py`), and optional YOLOv8-nano ONNX detection.
- **6-DOF Analytical Inverse Kinematics**: Fast closed-form geometric solver with reachability validation, automated adaptive pitch compensation for workspace boundaries, and joint limit enforcement.
- **Smooth Trajectory Generation**: Minimum-jerk polynomial interpolation with velocity bounding and 50 ms time-stepping.
- **Emergency Stop Safety**: Software and topic-level E-STOP immediately holds actuator positions and terminates active trajectories.
- **Real-Time Web Dashboard**: Built with FastAPI, WebSockets, and Vanilla HTML/CSS/JS. Streams camera perception feeds with live detection overlays, animated 3D arm skeleton, telemetry gauges, and interactive prompt console.

---

## 🛠️ Hardware Requirements

| Component | Specification |
|---|---|
| Single-Board Computer | Raspberry Pi 5 (8 GB recommended) |
| Robot Arm | LeArm / xArm Lite 6-DOF Manipulator |
| PWM Driver | PCA9685 16-Channel 12-bit I²C Board (Address `0x40`) |
| Camera | Raspberry Pi Camera Module 3 (Wide) mounted ~40 cm overhead |
| Microphone (Optional) | USB MEMS Microphone for voice commands |
| Power Supplies | 5V / 5A USB-C (Pi) + 6V / 3A-5A DC Barrel (Servos) |

*(See [`docs/hardware_assembly.md`](docs/hardware_assembly.md) for full wiring and power isolation schematics).*

---

## ⚡ Quickstart

### 1. Standalone Simulation & Web Dashboard (No Hardware Required)

You can run and test the complete pipeline immediately on Windows, macOS, or Linux:

```bash
# 1. Clone repository
git clone <repo-url>
cd "robot arm"

# 2. Install Python requirements
pip install -r requirements.txt

# 3. Launch the Web Dashboard
python scripts/run_simulation.py --dashboard --port 8000
```
Open your browser at **`http://localhost:8000`** to view the live vision feed, 3D kinematic skeleton, and send natural-language prompts!

### 2. Execute via Command Line
```bash
python scripts/run_simulation.py --command "pick up the red block and place it on the blue mat"
```

### 3. Run Automated Tests
```bash
python -m pytest tests/ -v
```
All 15 unit and integration tests validate the IK solver, perception homography, task planner, trajectory interpolation, and orchestrator.

---

## 🤖 Raspberry Pi 5 Deployment (ROS 2 Humble)

To deploy to physical hardware:

```bash
# 1. Run automated setup script
chmod +x scripts/*.sh
./scripts/setup_pi.sh

# 2. Download LLM / Whisper weights
./scripts/download_models.sh

# 3. Build ROS 2 workspace
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# 4. Launch full system
ros2 launch robot_arm_nlp full_system.launch.py
```

Or deploy using Docker:
```bash
docker-compose up --build
```

---

## 📁 Repository Structure

```
robot-arm-nlp/
├── .gitignore
├── README.md
├── requirements.txt
├── package.xml                  # ROS 2 package manifest
├── setup.py                     # ROS 2 Python entrypoints
├── setup.cfg
├── Dockerfile                   # Containerized ROS 2 environment
├── docker-compose.yml
├── config/
│   ├── colour_ranges.yaml       # HSV segmentation bounds
│   ├── servo_calibration.yaml   # PCA9685 channels & pulse limits
│   └── arm_dimensions.yaml      # Link lengths & workspace bounds
├── msg/
│   ├── ActionStep.msg           # Atomic step message
│   └── ActionList.msg           # Action plan array
├── srv/
│   └── GetObjects.srv           # Object perception service
├── urdf/
│   └── robot_arm.urdf           # 6-DOF manipulator kinematic model
├── launch/
│   └── full_system.launch.py    # ROS 2 full system launcher
├── src/
│   ├── input_handler/           # Text & voice capture nodes
│   ├── task_planner/            # LLM prompts, GGUF backend, Rule engine
│   ├── perception/              # HSV segmenter, Calibrator, YOLOv8
│   ├── motion/                  # 6-DOF IK solver, Trajectory, Servo driver
│   ├── orchestrator/            # Multi-step pipeline coordinator
│   └── simulation/              # Virtual arm kinematics & camera generator
├── web_dashboard/               # FastAPI + WebSocket live visualizer
│   ├── app.py
│   └── static/                  # Glassmorphic dark UI & 3D canvas
├── tests/                       # Complete pytest test suite (15 tests)
├── scripts/
│   ├── run_simulation.py        # Single simulation CLI
│   ├── setup_pi.sh              # Raspberry Pi automated installer
│   └── download_models.sh       # Model downloader
└── docs/
    ├── hardware_assembly.md     # Wiring & pinouts
    ├── calibration_guide.md     # Homography & HSV tuning
    └── deployment_guide.md      # Deployment walkthrough
```

---

## 🧪 Testing & Verification

The project includes unit and integration tests with 100% pass rate:
- `test_ik_solver.py`: Validates forward-inverse kinematics mathematical consistency, workspace bounds enforcement, and servo limits.
- `test_perception.py`: Validates HSV color segmentation, centroid localization, and homography pixel-to-world roundtrips.
- `test_task_planner.py`: Validates compound natural language parsing, pronoun resolution, and JSON action lists.
- `test_trajectory.py`: Validates minimum-jerk endpoint convergence and smooth velocity bounds.
- `test_orchestrator.py`: Validates the end-to-end vision-language-action loop with simulated hardware.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
