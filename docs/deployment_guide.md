# Deployment Guide

This system supports two primary operational modes:
1. **Physical Hardware Deployment (Raspberry Pi 5 + ROS 2 Humble)**
2. **Containerized Deployment (Docker / docker-compose)**
3. **Standalone Simulation Mode (Windows / macOS / Linux without ROS 2)**

---

## Mode 1: Native Raspberry Pi 5 (ROS 2 Humble)

### 1. One-Click Setup
On your Raspberry Pi 5 (running Ubuntu 22.04 / 24.04 or Raspberry Pi OS 64-bit with ROS 2 Humble):
```bash
git clone <your-github-repo-url>
cd "robot arm"
chmod +x scripts/*.sh
./scripts/setup_pi.sh
```

### 2. Download Models
```bash
./scripts/download_models.sh
```

### 3. Build the ROS 2 Workspace
```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 4. Launch Full Autonomous System
```bash
ros2 launch robot_arm_nlp full_system.launch.py
```
Or with voice control enabled:
```bash
ros2 launch robot_arm_nlp full_system.launch.py use_voice:=true
```

---

## Mode 2: Containerized Deployment (Docker)

To run the full stack inside Docker with access to host USB camera and I²C servo bus:
```bash
docker-compose up --build
```

---

## Mode 3: Standalone Simulation & Web Dashboard

To run without ROS 2, without a physical robot arm, and on any dev laptop:

### Run Interactive Web Dashboard
```bash
python scripts/run_simulation.py --dashboard --port 8000
```
Open **http://localhost:8000** in your browser to interact with the visualizer and natural language prompt console.

### Run Single Command via CLI
```bash
python scripts/run_simulation.py --command "pick up the red block and place it on the blue mat"
```

### Run Test Suite
```bash
python -m pytest tests/ -v
```
