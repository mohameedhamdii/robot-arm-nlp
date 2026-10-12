# System Calibration Guide

Precision pick-and-place requires three calibration procedures:
1. **Camera-to-World Homography Calibration** (Pixel to Real-world mm)
2. **HSV Color Threshold Tuning** (Lighting adaptation)
3. **Servo Pulse Width & Zero Alignment** (Joint angle calibration)

---

## 1. Camera Homography Calibration

Homography maps camera pixel coordinates `(u, v)` to physical workspace coordinates `(x, y)` in millimeters relative to the arm's base.

### Procedure:
1. Print a standard **7 × 7 checkerboard grid** with **25 mm square size**.
2. Place the checkerboard flat on the workspace directly under the camera.
3. Capture a calibration photo or run:
   ```bash
   python src/perception/calibrate.py path/to/checkerboard_image.jpg
   ```
4. The script detects internal corner junctions using `cv2.findChessboardCorners` and `cv2.cornerSubPix`, computes the 3 × 3 homography transformation matrix, and saves it to:
   ```
   config/homography.npy
   ```
5. Verification:
   Run the perception test to confirm pixel-to-world conversion:
   ```bash
   python -m pytest tests/test_perception.py -k test_camera_calibrator_transform_roundtrip
   ```

---

## 2. HSV Color Segmentation Tuning

Ambient lighting varies across environments. Use the interactive tuner to adjust HSV filter ranges for blocks and mats.

### Procedure:
1. Place the coloured blocks (red, blue, green, yellow) and mats on the table.
2. Run the interactive tuning GUI:
   ```bash
   python src/perception/tune_hsv.py 0
   ```
3. Adjust the trackbars:
   - `H_min` / `H_max`: Hue boundaries (0–180)
   - `S_min` / `S_max`: Saturation boundaries (0–255)
   - `V_min` / `V_max`: Value / Brightness boundaries (0–255)
4. Press **`s`** in the window and enter the color name (e.g. `red`) to automatically update `config/colour_ranges.yaml`.
5. Press **`q`** to quit when done.

---

## 3. Servo Pulse Width & Zero Calibration

Ensure each servo joint matches physical angles (0° to 180°).

1. In `config/servo_calibration.yaml`, verify the channel configuration:
   ```yaml
   servos:
     base_yaw:
       channel: 0
       min_pulse_us: 500
       max_pulse_us: 2500
       min_angle: 0.0
       max_angle: 180.0
       center_offset_deg: 0.0
   ```
2. If joint angle 90° does not point directly forward, adjust `center_offset_deg` (e.g. `+5.0` or `-3.0`) until mechanically squared.
