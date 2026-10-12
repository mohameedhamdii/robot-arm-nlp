# Plan 01 — Natural-Language-Controlled Robot Arm

> **One-liner:** Tell the arm "pick up the red block, place it on the blue mat" — it plans and executes autonomously.

---

## 1. Project Overview

### 1.1 Goal
Build a robotic arm system that accepts free-form natural-language commands, interprets them with an LLM-based task planner, identifies target objects via computer vision, plans collision-free trajectories, and executes multi-step pick-and-place sequences — all orchestrated from a Raspberry Pi 5.

### 1.2 Domain
Robotics & Manipulation

### 1.3 Target Audience / Portfolio Value
Demonstrates the industry shift from hard-coded motion scripts to goal-based execution using vision-language-action pipelines. Shows mastery of ROS 2, motion planning, on-device LLM inference, and real-time CV — all on embedded hardware.

---

## 2. Hardware Bill of Materials

| Component | Specific Part / Model | Qty | Purpose |
|---|---|---|---|
| Single-board computer | Raspberry Pi 5 (8 GB) | 1 | Main compute node — runs ROS 2, LLM, CV |
| Robot arm | LeArm / xArm Lite 6-DOF servo arm | 1 | Physical manipulator |
| Servo driver | PCA9685 16-channel PWM board | 1 | Drives 6 servos from I²C |
| Camera | Raspberry Pi Camera Module 3 (wide) | 1 | Top-down workspace view |
| Microphone | USB MEMS mic (e.g., ReSpeaker USB) | 1 | Voice input (optional — can also use text) |
| Power supply | 5 V / 5 A USB-C (Pi) + 6 V / 3 A barrel (servos) | 2 | Separate power rails |
| Workspace surface | Flat board ≈ 40 × 40 cm | 1 | Consistent background for CV |
| Coloured blocks | 3D-printed or wooden cubes (red, blue, green, yellow) | 6–8 | Manipulation targets |
| Coloured mats | Felt squares matching block colours | 4 | Placement targets |
| MicroSD card | 64 GB A2 U3 | 1 | OS + software |
| Cables & standoffs | Jumper wires, I²C cable, mounting hardware | — | Assembly |

### 2.1 Hardware Setup Notes
- Mount the camera directly above the workspace using a gooseneck or 3D-printed bracket, aimed straight down for a bird's-eye view.
- Keep the servo power supply separate from the Pi power supply to avoid brownouts during simultaneous servo moves.
- Use a calibration grid (printed checkerboard) to map pixel coordinates to real-world XY workspace coordinates.

---

## 3. Software Stack & Dependencies

| Layer | Technology | Version / Notes |
|---|---|---|
| OS | Raspberry Pi OS (64-bit, Bookworm) | — |
| Middleware | ROS 2 Humble | Full desktop install or base + MoveIt |
| Motion planning | MoveIt 2 | With servo controller interface |
| Language model | llama.cpp | Running a quantized ≤ 3 B param GGUF model (e.g., Phi-3-mini-4k, TinyLlama) |
| Computer vision | OpenCV 4.x + NumPy | Colour segmentation, contour detection |
| Object detection (opt.) | YOLOv8-nano (Ultralytics) | For robust multi-class detection |
| Speech-to-text (opt.) | whisper.cpp (tiny/base model) | For voice commands |
| Programming language | Python 3.11 | Primary; C++ for performance-critical nodes |
| Build system | colcon (ROS 2) | — |
| Servo control library | adafruit-circuitpython-servokit | Via I²C to PCA9685 |

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    USER INPUT                            │
│         (text terminal  /  voice via whisper.cpp)        │
└──────────────┬───────────────────────────────────────────┘
               │  raw text command
               ▼
┌──────────────────────────────────────────────────────────┐
│             NLP / LLM TASK PLANNER NODE                  │
│  • Receives natural-language command                     │
│  • Calls llama.cpp with a structured prompt              │
│  • Outputs a JSON action list:                           │
│      [{"action":"pick","object":"red block"},            │
│       {"action":"place","target":"blue mat"}]            │
└──────────────┬───────────────────────────────────────────┘
               │  action list (JSON)
               ▼
┌──────────────────────────────────────────────────────────┐
│            VISION / PERCEPTION NODE                      │
│  • Captures frame from Pi Camera                         │
│  • Segments objects by colour (HSV masks) or YOLO        │
│  • Returns object centroids in pixel coords              │
│  • Transforms pixels → workspace XY via homography       │
└──────────────┬───────────────────────────────────────────┘
               │  object poses (x, y, z_fixed)
               ▼
┌──────────────────────────────────────────────────────────┐
│         MOTION PLANNING & EXECUTION NODE                 │
│  • Receives target pose for each action                  │
│  • Computes inverse kinematics (IK) for 6-DOF arm       │
│  • Plans trajectory (MoveIt 2 or custom IK solver)       │
│  • Sends joint angles to PCA9685 via servo driver        │
│  • Executes: approach → grip → lift → move → place       │
└──────────────┬───────────────────────────────────────────┘
               │  servo PWM signals
               ▼
┌──────────────────────────────────────────────────────────┐
│               PHYSICAL ROBOT ARM                         │
│   6-DOF arm + gripper executing the planned motion       │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Detailed Module Breakdown

### 5.1 Module A — Input Handler (`input_handler_node`)

**Responsibility:** Accept user commands via terminal text or microphone.

**Implementation details:**
1. **Text mode (default):** A ROS 2 node subscribes to a `/user_command` topic (type `std_msgs/String`). A simple CLI script publishes typed text to this topic.
2. **Voice mode (optional):** Record 5-second audio chunks from the USB mic, run whisper.cpp (tiny model, English) to transcribe, publish the resulting text to `/user_command`.
3. Publish only when a complete command is detected (silence threshold or Enter key).

**Files to create:**
- `src/input_handler/input_handler_node.py`
- `src/input_handler/voice_capture.py` (optional)

---

### 5.2 Module B — LLM Task Planner (`task_planner_node`)

**Responsibility:** Convert a free-form English sentence into an ordered list of atomic robot actions.

**Implementation details:**
1. Subscribe to `/user_command`.
2. Construct a **system prompt** that instructs the LLM to output **only** valid JSON. Example system prompt:

```
You are a robot task planner. Given a natural-language instruction and a list of known objects and locations, output a JSON array of steps.
Each step is an object with keys:
  "action": one of "pick", "place", "move_to", "open_gripper", "close_gripper"
  "object": the name of the target object (for pick) or null
  "target": the name of the destination (for place) or null
Only use objects and targets from the provided list. Output ONLY the JSON array, nothing else.
```

3. Prepend the system prompt with a **context block** listing currently visible objects (received from the vision node via a service call or topic).
4. Call llama.cpp via its Python bindings (`llama-cpp-python`) with temperature = 0.0 for deterministic output.
5. Parse the returned JSON. If parsing fails, retry once with a stricter prompt.
6. Publish the action list to `/planned_actions` (custom message type `ActionList`).

**Custom ROS 2 message:**
```
# ActionStep.msg
string action
string object_name
string target_name
```
```
# ActionList.msg
ActionStep[] steps
```

**Files to create:**
- `src/task_planner/task_planner_node.py`
- `src/task_planner/prompt_templates.py`
- `msg/ActionStep.msg`
- `msg/ActionList.msg`

---

### 5.3 Module C — Vision / Perception (`perception_node`)

**Responsibility:** Detect and locate objects and target zones on the workspace.

**Implementation details:**
1. Capture frames from the Pi Camera via `picamera2` library at 640 × 480.
2. **Colour segmentation pipeline:**
   - Convert frame to HSV colour space.
   - For each known object colour (red, blue, green, yellow), apply an HSV range mask.
   - Find contours, filter by area (min 500 px²), compute centroids.
   - Label each detection with its colour + type (block vs. mat, distinguished by contour area — mats are larger).
3. **Pixel-to-world transform:**
   - During initial calibration, photograph a printed 7 × 7 checkerboard on the workspace.
   - Compute a homography matrix (`cv2.findHomography`) mapping pixel coords to mm coords in the arm's coordinate frame.
   - Store the homography matrix as a NumPy `.npy` file.
4. **Alternative: YOLO detection (optional upgrade):**
   - Train YOLOv8-nano on a small custom dataset (≈200 labelled images of the blocks and mats) or use colour-coded class labels.
   - Export to ONNX, run inference with OpenCV DNN backend.
5. Publish detections to `/detected_objects` topic (custom message with name, x, y, confidence).
6. Provide a ROS 2 service `/get_objects` that returns the latest detection list on demand (used by the task planner for context).

**Calibration procedure (documented for AI builder):**
1. Place checkerboard on workspace.
2. Run `python3 calibrate.py` — captures image, detects corners, computes homography, saves `homography.npy`.
3. Verify by clicking points in the image and comparing printed world coords.

**Files to create:**
- `src/perception/perception_node.py`
- `src/perception/colour_segmentation.py`
- `src/perception/calibrate.py`
- `src/perception/yolo_detector.py` (optional)
- `config/colour_ranges.yaml` (HSV min/max for each colour)

---

### 5.4 Module D — Motion Planning & Execution (`motion_node`)

**Responsibility:** Convert target workspace coordinates into joint angles and drive the servos.

**Implementation details:**
1. **Arm kinematics:**
   - Define the arm's URDF (Unified Robot Description Format) with accurate link lengths measured from the physical arm.
   - Use MoveIt 2's IK solver or implement a geometric IK solver for a 6-DOF arm (faster, no MoveIt dependency).
   - Geometric IK approach: solve for base rotation, then shoulder/elbow angles via law of cosines, then wrist pitch/roll for vertical gripper orientation.
2. **Pick-and-place sequence for each action pair:**
   ```
   open_gripper()
   move_to(object_x, object_y, z=hover_height)     # approach from above
   move_to(object_x, object_y, z=grasp_height)      # descend to object
   close_gripper()
   move_to(object_x, object_y, z=hover_height)       # lift
   move_to(target_x, target_y, z=hover_height)       # transit to target
   move_to(target_x, target_y, z=place_height)        # descend
   open_gripper()
   move_to(target_x, target_y, z=hover_height)        # retract
   move_to(home_x, home_y, home_z)                    # return home
   ```
3. **Trajectory interpolation:**
   - Linearly interpolate joint angles between start and end in N steps (e.g., 20 steps over 1 second).
   - Send each step to the PCA9685 with a 50 ms delay for smooth motion.
4. **Servo driver:**
   - Use `adafruit_servokit.ServoKit(channels=16)` to set angles.
   - Map joint angles (degrees) to servo pulse widths; store calibration offsets in `config/servo_calibration.yaml`.
5. **Safety limits:**
   - Enforce joint angle limits per servo (e.g., 0°–180°).
   - Enforce workspace boundary box — reject targets outside reachable area.
   - Emergency stop: subscribe to `/estop` topic; if received, immediately hold current position.

**Files to create:**
- `src/motion/motion_node.py`
- `src/motion/ik_solver.py`
- `src/motion/servo_driver.py`
- `src/motion/trajectory.py`
- `urdf/robot_arm.urdf`
- `config/servo_calibration.yaml`
- `config/arm_dimensions.yaml`

---

### 5.5 Module E — Orchestrator (`orchestrator_node`)

**Responsibility:** Coordinates the full pipeline end-to-end.

**Implementation details:**
1. Subscribe to `/planned_actions`.
2. For each `ActionStep` in the list:
   a. Call `/get_objects` service to get latest object positions.
   b. Look up the coordinates of `object_name` and `target_name`.
   c. If object not found, re-scan (request fresh perception frame) up to 3 times, then abort with error message.
   d. Send pick coordinates to motion node, wait for completion.
   e. Send place coordinates to motion node, wait for completion.
3. After all steps complete, publish a result summary to `/task_result` and print to terminal.
4. Handle errors gracefully: if IK fails (unreachable point), report back which step failed and why.

**Files to create:**
- `src/orchestrator/orchestrator_node.py`

---

## 6. Directory Structure

```
robot-arm-nlp/
├── README.md
├── requirements.txt
├── setup.py
├── package.xml
├── config/
│   ├── colour_ranges.yaml
│   ├── servo_calibration.yaml
│   └── arm_dimensions.yaml
├── msg/
│   ├── ActionStep.msg
│   └── ActionList.msg
├── urdf/
│   └── robot_arm.urdf
├── launch/
│   └── full_system.launch.py
├── src/
│   ├── input_handler/
│   │   ├── __init__.py
│   │   ├── input_handler_node.py
│   │   └── voice_capture.py
│   ├── task_planner/
│   │   ├── __init__.py
│   │   ├── task_planner_node.py
│   │   └── prompt_templates.py
│   ├── perception/
│   │   ├── __init__.py
│   │   ├── perception_node.py
│   │   ├── colour_segmentation.py
│   │   ├── calibrate.py
│   │   └── yolo_detector.py
│   ├── motion/
│   │   ├── __init__.py
│   │   ├── motion_node.py
│   │   ├── ik_solver.py
│   │   ├── servo_driver.py
│   │   └── trajectory.py
│   └── orchestrator/
│       ├── __init__.py
│       └── orchestrator_node.py
├── tests/
│   ├── test_task_planner.py
│   ├── test_perception.py
│   ├── test_ik_solver.py
│   └── test_orchestrator.py
└── docs/
    ├── calibration_guide.md
    └── hardware_assembly.md
```

---

## 7. Configuration Files — Contents

### 7.1 `config/colour_ranges.yaml`
```yaml
colours:
  red:
    hsv_lower: [0, 120, 70]
    hsv_upper: [10, 255, 255]
    hsv_lower_2: [170, 120, 70]
    hsv_upper_2: [180, 255, 255]
  blue:
    hsv_lower: [100, 120, 70]
    hsv_upper: [130, 255, 255]
  green:
    hsv_lower: [40, 70, 70]
    hsv_upper: [80, 255, 255]
  yellow:
    hsv_lower: [20, 100, 100]
    hsv_upper: [35, 255, 255]

detection:
  min_contour_area_block: 500
  max_contour_area_block: 5000
  min_contour_area_mat: 5000
  max_contour_area_mat: 50000
```

### 7.2 `config/arm_dimensions.yaml`
```yaml
base_height: 65
shoulder_length: 105
elbow_length: 100
wrist_length: 70
gripper_length: 55

workspace:
  x_min: -150
  x_max: 150
  y_min: 50
  y_max: 250
  z_min: 0
  z_max: 200

hover_height: 80
grasp_height: 15
place_height: 20
```

---

## 8. LLM Prompt Engineering

### 8.1 System Prompt (stored in `prompt_templates.py`)
```
You are a robot arm task planner. You receive:
1. A natural-language instruction from the user.
2. A list of objects currently visible on the workspace with their names.

Your job is to output a JSON array of atomic steps the robot must execute. Each step is a JSON object:
{
  "action": "pick" | "place",
  "object_name": "<name of object to pick, e.g. 'red_block'>",
  "target_name": "<name of destination, e.g. 'blue_mat'>"
}

Rules:
- Only use object and target names from the provided visible objects list.
- "pick" requires "object_name" to be set and "target_name" to be null.
- "place" requires "target_name" to be set and "object_name" to be null.
- A "place" must always follow a "pick".
- If the instruction is ambiguous or impossible, output: {"error": "<reason>"}.
- Output ONLY valid JSON. No explanation, no markdown, no extra text.
```

### 8.2 Example User Prompt Construction
```
Visible objects: red_block, blue_block, green_block, red_mat, blue_mat, green_mat

User instruction: "Put the red block on the blue mat and the green block on the red mat"
```

### 8.3 Expected LLM Output
```json
[
  {"action": "pick", "object_name": "red_block", "target_name": null},
  {"action": "place", "object_name": null, "target_name": "blue_mat"},
  {"action": "pick", "object_name": "green_block", "target_name": null},
  {"action": "place", "object_name": null, "target_name": "red_mat"}
]
```

---

## 9. Calibration & Setup Procedure

1. **Assemble arm** on workspace board. Secure base with screws or clamps.
2. **Connect servos** to PCA9685 channels 0–5. Connect PCA9685 to Pi via I²C (SDA/SCL).
3. **Mount camera** directly above centre of workspace, ≈ 40 cm height, pointing straight down.
4. **Flash Raspberry Pi OS 64-bit** to SD card. Boot, connect to Wi-Fi.
5. **Install ROS 2 Humble** following official ARM64 install guide.
6. **Install Python dependencies:** `pip install opencv-python-headless numpy llama-cpp-python adafruit-circuitpython-servokit picamera2 pyyaml`.
7. **Download LLM model:** Place a quantized GGUF file (e.g., `phi-3-mini-4k-instruct.Q4_K_M.gguf`) into `models/`.
8. **Run servo calibration:** Move each joint to known angles, record PWM-to-angle mapping in `servo_calibration.yaml`.
9. **Run camera calibration:** Place checkerboard, run `calibrate.py`, verify homography.
10. **Run colour calibration:** Place each block and mat under workspace lighting, tune HSV ranges in `colour_ranges.yaml` using the provided tuning script (slider GUI).
11. **Launch full system:** `ros2 launch robot_arm_nlp full_system.launch.py`.
12. **Test with a simple command:** `"pick up the red block"` — verify full pipeline.

---

## 10. Testing Strategy

| Test | Type | What it validates |
|---|---|---|
| `test_task_planner.py` | Unit | LLM prompt → correct JSON action list for 10 sample commands |
| `test_perception.py` | Unit | Given sample images, correct object centroids and labels returned |
| `test_ik_solver.py` | Unit | Given workspace coords, correct joint angles computed; out-of-range coords rejected |
| `test_orchestrator.py` | Integration | Mock vision + motion nodes; verify correct sequencing of picks and places |
| Manual end-to-end | System | Speak/type 5 varied commands, observe physical arm completing tasks correctly |

---

## 11. Stretch Goals / Future Enhancements

- **Obstacle avoidance:** Add workspace obstacle detection and plan around them.
- **Multi-turn dialogue:** "No, I meant the small red block" — context-aware re-planning.
- **Depth estimation:** Replace fixed Z heights with actual depth from a stereo camera or ToF sensor.
- **Web dashboard:** Livestream the camera feed with detection overlays and a command input box.
- **Voice feedback:** Use a TTS engine to have the robot confirm actions: "Picking up the red block now."

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM outputs malformed JSON | Pipeline stalls | Retry with stricter prompt; fall back to regex parsing |
| Servo jitter / inaccuracy | Missed grasps | Use high-quality digital servos; add closed-loop feedback with vision verification |
| Lighting changes break CV | Wrong object detection | Use controlled lighting (LED strip around workspace); provide HSV tuning script |
| Pi 5 thermal throttling under LLM + CV load | Slow response | Add heatsink + fan; use smaller quantized model |
| IK solution unreachable | Arm can't reach target | Validate reachability before attempting; report error to user |

---

## 13. Estimated Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| Hardware assembly & wiring | 2 days | Working arm on workspace |
| Servo calibration & basic motion | 2 days | Arm moves to commanded joint angles |
| Camera calibration & CV pipeline | 3 days | Objects detected and localised |
| IK solver & pick-and-place sequence | 3 days | Arm picks and places at given coords |
| LLM integration & prompt tuning | 3 days | NL command → action list working |
| Orchestrator & end-to-end integration | 2 days | Full pipeline functional |
| Testing, tuning, documentation | 2 days | Reliable demo |
| **Total** | **~17 days** | — |
