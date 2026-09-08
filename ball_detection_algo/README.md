# Golf Ball Detection (v1)

White-golf-ball detector for the autonomous golf ball picker robot. Opens a USB
webcam, finds white golf balls in each frame using classical computer vision
(HSV color thresholding + contour shape filtering — no ML), and draws a bounding
box around each one.

This code is written to run **unchanged on the Raspberry Pi 5**; the laptop is
just the development environment.

## Files

| File | What it does |
|---|---|
| `detector.py` | Core detection logic. `detect_golf_balls(frame)` is a pure function (no camera/window/disk) — the piece that plugs into the robot's state machine. |
| `camera.py` | Opens a USB webcam with the right backend per OS (Windows/Linux). |
| `list_cameras.py` | Probe tool to find which camera index is the USB webcam. |
| `calibrate.py` | **Auto-tune**: box a few real golf balls, and it computes thresholds for you and saves them to a JSON file. |
| `tune.py` | Live trackbar tuner for hand-adjusting thresholds. |
| `run_webcam.py` | Main live detector on the webcam. |
| `test_image.py` | Run detection on a still image (no camera). |

## Setup

Any **Python 3.9-3.14** works — `pip install` pulls prebuilt wheels for OpenCV
and NumPy (no compiling). A virtual environment is recommended.

### Windows (dev laptop)
```powershell
# from ball_detection_algo/
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Raspberry Pi 5 (Bookworm)
```bash
python3 -m venv .venv          # venv is required on Bookworm (PEP 668)
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# 1. Find the USB webcam's index (not the laptop's built-in camera):
python list_cameras.py

# 2. AUTO-TUNE for your lighting: box a few real golf balls; params are saved.
python calibrate.py --camera 1                 # writes params.json

# 3. Run the live detector using those tuned params:
python run_webcam.py --camera 1 --params params.json

# Offline: test detection on a saved photo, no camera needed:
python test_image.py some_photo_of_balls.jpg
```

Press `q` to quit any live window.

## Tuning

White-ball detection is lighting-sensitive — the same thresholds rarely work in
two different rooms. Two ways to tune:

### Auto-tune (recommended): `calibrate.py`
Learns the thresholds from real golf balls instead of guessing.

```bash
python calibrate.py --camera 1              # or: --image photo.jpg
```
Press SPACE to freeze a frame, drag a box around each golf ball (ENTER after
each; ENTER on an empty box when done), and it measures the balls' actual
brightness/saturation and writes the settings to `params.json`. Then run any
script with `--params params.json`. Re-calibrate whenever the lighting changes.

### Manual: `tune.py`
Live trackbars if you want to hand-tweak. Start from a calibration file and save
your changes back:
```bash
python tune.py --camera 1 --params params.json --out params.json
```
The right pane shows the raw white mask, so you can see exactly what the color
gate selects before shape filtering.

### If detection is still off
- **Missing balls** → lower `val_min` (accept dimmer whites) or raise `sat_max`.
- **Boxing bright non-balls** (lines, glare, shoes) → raise `min_circularity` /
  `min_fill_ratio`, or tighten `min_area`/`max_area` for your camera distance.

## Running on the Raspberry Pi 5

- **USB webcam:** everything above works as-is (`cv2.VideoCapture` uses V4L2 on
  Linux). The USB cam is usually index `0` on the RP5.
- **Headless robot (no monitor):** add `--no-display` to `run_webcam.py`. Use
  `--save out.jpg` to write the latest annotated frame, or import
  `detect_golf_balls()` directly and feed the boxes to the navigation code.
- **If you switch to the Pi CSI camera module** (ribbon cable, not USB): that
  camera uses libcamera and needs **Picamera2** to capture frames — grab a frame
  with Picamera2 and pass it to `detect_golf_balls()`. The detector itself
  doesn't change; only `camera.py`/the capture call would.

## What this version does NOT do (future work)

Distance/size estimation, tracking a ball across frames, handing targets to
navigation, and ML-based detection (e.g. YOLO) — all deferred until basic
detection is reliable on the real green.
