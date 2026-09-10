# Golf Ball Detection

Golf-ball detector for the autonomous golf ball picker robot. Opens a USB webcam,
finds golf balls in each frame, and draws a bounding box around each one.

Two interchangeable detection backends:

| Backend | How it works | Use it for |
|---|---|---|
| `classical` (default) | HSV white-thresholding + morphology + contour shape gates. No ML, no dependencies beyond OpenCV. | Fast, predictable, controlled/indoor light. The fallback. |
| `yolo` | Ultralytics YOLO11n neural detector. | Shade, uneven outdoor light, and balls at distance, where fixed thresholds fail. |

Both satisfy the same contract, `detector(frame) -> list[Detection]`, so
navigation and the autonomous state machine never learn which one ran. Pick with
`--backend`.

This code is written to run **unchanged on the Raspberry Pi 5**; the laptop is
just the development environment.

## Files

| File | What it does |
|---|---|
| `detector.py` | Classical detection logic and the shared `Detection` type. `detect_golf_balls(frame, params)` is a pure function. Imports no ML libraries, by design. |
| `yolo_detector.py` | `YoloDetector`, the neural backend. A callable object, because a model must be loaded once and reused. |
| `backends.py` | `make_detector(...)` factory plus the shared CLI flags. The only module importing both detectors. |
| `camera.py` | Opens a USB webcam with the right backend per OS (Windows/Linux). |
| `list_cameras.py` | Probe tool to find which camera index is the USB webcam. |
| `calibrate.py` | **Classical auto-tune**: box a few real golf balls and it computes thresholds. |
| `tune.py` | Live trackbar tuner for hand-adjusting classical thresholds. |
| `run_webcam.py` | Main live detector on the webcam. |
| `test_image.py` | Run detection on a still image (no camera). |
| `benchmark.py` | Run both backends over a folder and compare, side by side. |
| `capture_dataset.py` | Collect training images from the webcam. |

## Setup

Any **Python 3.9-3.14** works. A virtual environment is recommended.

```bash
python3 -m venv .venv           # venv is required on RP5 Bookworm (PEP 668)
source .venv/bin/activate       # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

That is everything the classical backend needs. The YOLO backend is **optional**
and installed separately, because `ultralytics` pulls in torch.

**Install CPU-only torch first.** Installing `ultralytics` straight away drags in
torch's default CUDA build: the wheel, cuDNN, and the NVIDIA runtime libraries
total several GB. No machine on this project has an NVIDIA GPU, and the Raspberry
Pi 5 is ARM, so all of it is dead weight.

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
pip install -r requirements-yolo.txt
```

The second command sees torch already satisfied and leaves it alone. Train on a
CUDA machine or Colab instead, and bring back only the weights.

Keeping the two requirement files apart is deliberate: if inference is too slow on
the robot, the classical backend still runs on a machine with only OpenCV and
NumPy.

## Usage

```bash
# 1. Find the USB webcam's index (not the laptop's built-in):
python list_cameras.py

# 2a. Classical: auto-tune for your lighting, then run.
python calibrate.py --camera 1                              # writes params.json
python run_webcam.py --camera 1 --params params.json

# 2b. YOLO: no tuning step, works out of the box.
python run_webcam.py --camera 1 --backend yolo

# Offline: test either backend on a saved photo.
python test_image.py photo.jpg --backend yolo
```

Press `q` to quit any live window.

## Choosing a backend

The classical detector fails in two specific ways, and both are inherent rather
than a tuning mistake:

- **Shade and uneven light.** It accepts a pixel only above a fixed brightness,
  so a ball in shadow drops out. Lowering the threshold to catch it starts
  boxing bright grass and concrete instead. There is no setting that survives a
  green with both sun and shade on it.
- **Distance.** Calibration sets an area floor from the balls you boxed. Balls
  further away fall below it and are discarded before the shape checks run.

YOLO keys on shape and context rather than absolute brightness, so it handles
both. It costs roughly an order of magnitude more compute per frame.

Run `benchmark.py` on your own photos rather than taking the above on faith:

```bash
python benchmark.py photos/ --params params.json --out comparison/
```

It reports per-image counts for both backends and writes side-by-side annotated
pairs. Counts alone don't prove correctness, so open the comparisons and confirm
the extra boxes are real balls.

## Tuning the classical backend

White-ball detection is lighting-sensitive; the same thresholds rarely work in
two different rooms.

### Auto-tune (recommended): `calibrate.py`
```bash
python calibrate.py --camera 1              # or: --image photo.jpg
```
Press SPACE to freeze a frame, drag a box around each golf ball (ENTER after
each; ENTER on an empty box when done). Re-calibrate whenever lighting changes.

**Calibrate at the distance the robot will actually see balls from.** Boxing
balls held close to the camera sets an area floor that rejects everything on the
far half of the green.

### Manual: `tune.py`
```bash
python tune.py --camera 1 --params params.json --out params.json
```
The right pane shows the raw white mask, so you can see what the color gate
selects before shape filtering.

### If detection is still off
- **Missing balls** → lower `val_min` (accept dimmer whites) or raise `sat_max`.
- **Missing distant balls** → lower `min_area`.
- **Boxing bright non-balls** → raise `min_circularity` / `min_fill_ratio`, or
  tighten `min_area`/`max_area`.

## Training a custom YOLO model

The default `--backend yolo` runs **zero-shot**: stock COCO weights filtered to
the `sports ball` class (id 32), which already finds golf balls with no labelling
at all. Use it to decide whether the ML path is worth pursuing before investing
in a dataset.

To go further, train a single-class model:

1. **Capture.** `python capture_dataset.py --camera 1 --out datasets/raw`
   Shoot the conditions that currently fail: shade, overcast, low sun, balls at
   range. Include frames with no balls. Shoot from the robot's camera height.
2. **Label.** Roboflow or CVAT, exported in YOLO format, one class: `ball`.
   200-500 images is a reasonable target for a single-class detector.
3. **Train.** Off this machine. It has no CUDA GPU, so a local run takes many
   hours against roughly half an hour on a free Colab T4.
   ```bash
   yolo detect train model=yolo11n.pt data=data.yaml epochs=100 imgsz=640
   ```
   Leave HSV and scale augmentation on; lighting invariance is the entire point.
4. **Use it.** Pass the weights and disable the COCO class filter, since a
   single-class model has no class 32:
   ```bash
   python run_webcam.py --camera 1 --backend yolo --model best.pt --coco-class -1
   ```

## Running on the Raspberry Pi 5

- **USB webcam:** everything above works as-is (`cv2.VideoCapture` uses V4L2 on
  Linux). The USB cam is usually index `0` on the RP5.
- **Headless robot (no monitor):** add `--no-display` to `run_webcam.py`. Use
  `--save out.jpg` to write the latest annotated frame, or import the detector
  directly and feed the boxes to the navigation code.
- **YOLO on the Pi:** export to NCNN, which is meaningfully faster than PyTorch
  on ARM. `--model` loads the exported directory through the same code path.
  ```bash
  yolo export model=best.pt format=ncnn
  python run_webcam.py --camera 0 --backend yolo --model best_ncnn_model --coco-class -1
  ```
  Expect a few frames per second on the CPU. That is adequate for a robot that
  stops, scans, then drives. If it isn't, fall back to `--backend classical` or
  add a Hailo AI HAT+.
- **Small distant balls** are hard for YOLO too: at `--imgsz 640` a 720p frame is
  halved, so a 15 px ball becomes ~7 px. Raise `--imgsz` to 960 (slower), or let
  the robot drive closer and re-scan, which is the better robotics answer.
- **If you switch to the Pi CSI camera module** (ribbon cable, not USB): that
  uses libcamera and needs **Picamera2** to capture frames. Only `camera.py`
  changes; neither detector does.

## Not done yet (future work)

Distance/size estimation, tracking a ball across frames, and handing targets to
navigation. A raw `onnxruntime` backend, which would drop the torch dependency on
the Pi to about a tenth the size, if the install footprint becomes a problem.
