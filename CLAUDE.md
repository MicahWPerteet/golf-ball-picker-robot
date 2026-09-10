# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Senior capstone for an **Autonomous Golf Ball Picker Robot** — a periodically-operating robot that scans a putting/chipping green (~every 30 min), collects golf balls, returns to a base station, and unloads them into a ball-stacking system. See `capstone_robot_system_plan.md` for the authoritative, up-to-date system concept, decision records, bill of materials, and open questions. **Read that document before making design or component recommendations** — it records decisions already made and their rationale, so proposing alternatives to settled choices (e.g. the controller) needs to engage with the reasoning there.

This is an **early-stage repository**: planning docs, CAD, and the first computer-vision code (`ball_detection_algo/`, see below). There is no repo-wide build system or CI; the only runnable code lives in the CV module and is driven by the scripts documented there.

## Repository layout

- `capstone_robot_system_plan.md` — the single source of truth for the project. Update it when design decisions change rather than duplicating its content elsewhere.
- `ball_holder_model/` — Blender sources (`.blend`) and exported meshes (`.stl`) for the physical ball-holder fixture, iterated by version (`v1`, `v1.1`, `v1.2`). `.blend1` files are Blender's automatic backups. When adding an iteration, bump the version suffix and export a matching `.stl` alongside the `.blend`. **These files are git-ignored** (large binaries, no useful diff) — they exist on disk and are shared out-of-band, so don't assume a clone has them.
- `ball_detection_algo/` — the computer-vision ball-detection code (Python + OpenCV). See the dedicated section below.

## Key settled decisions (from the plan doc)

- **Controller: Raspberry Pi 5**, chosen over the ESP32-P4 primarily for its Linux/Python/OpenCV vision ecosystem, built-in Wi-Fi, and lower project risk. The RP5 is the high-level brain; a **custom KiCad PCB** handles power distribution, motor-driver interfaces, and charging/docking — this is where the embedded-systems learning goal lives.
- **Drivetrain:** planned four-wheel drive with 4+ motor drivers. Keep **motor power and logic/computer power on separate rails**.
- **Vision:** YOLO11n neural detection is the primary path, with classical CV retained as a
  selectable fallback (see section 5 of the plan doc for the decision record). Still a
  high-value but *not top-priority* capability (priority #4) — hardware reliability
  (drivetrain, collection, return-to-dock) comes first.

## Computer-vision module (`ball_detection_algo/`)

Detects golf balls in a USB-webcam feed and draws a bounding box around each.
Written to run **unchanged on the RP5** (Linux/V4L2); the laptop is just the dev box.
See `ball_detection_algo/README.md` for full usage.

**Design (deliberate, don't flatten it):** there are **two interchangeable backends**
behind one contract, `detector(frame) -> list[Detection]`, selected with `--backend`:

- **`classical`** — HSV white-thresholding + morphology + contour shape-gating (area,
  circularity, fill-ratio). Lives in `detector.py` as a **pure
  `detect_golf_balls(frame, params)`** (no camera/window/disk). All thresholds sit in one
  `DetectorParams` dataclass serialized to `params.json`, which is git-ignored because it is
  per-camera, per-lighting output of `calibrate.py`.
- **`yolo`** — Ultralytics YOLO11n in `yolo_detector.py`. A **callable object, not a pure
  function**, because the model must be loaded once and reused across frames.

`backends.py` holds the `make_detector()` factory and the shared CLI flags, and is the only
module importing both. **`detector.py` must never import `ultralytics` or `torch`** — that
separation is what keeps the classical path runnable on a bare OpenCV install, which is the
fallback if RP5 inference is too slow. The ML import is deferred into `YoloDetector.__init__`.

Detection stays an isolated node in the autonomous state machine (…→ scan → navigate →…);
swapping backends does not touch navigation. Camera capture, tuning, and display live in
separate scripts that call into the factory.

**Environment:** a venv lives at `ball_detection_algo/.venv`. Run scripts with
`.venv\Scripts\python.exe` (Windows) / `.venv/bin/python` (RP5). `pip install -r
requirements.txt` pulls prebuilt wheels on any Python 3.9–3.14 (OpenCV ships an abi3 wheel);
no version pin is needed despite the local Python being 3.14. **`requirements-yolo.txt` is
separate and optional** — it adds `ultralytics` (and torch, which is large). Keep the base
requirements file free of ML dependencies.

**Typical workflow:** `list_cameras.py` (find the USB cam's index — it is *not* the laptop's
built-in) → then either `calibrate.py --camera N` → `run_webcam.py --camera N --params
params.json` for the classical path, or `run_webcam.py --camera N --backend yolo` for the
neural one. `tune.py` is the manual slider fallback; `test_image.py` runs either backend on a
still photo; `benchmark.py` compares both over a folder; `capture_dataset.py` collects
training images.

**YOLO status:** `--backend yolo` currently runs **zero-shot** on stock COCO weights,
filtered to class 32 (`sports ball`), which needs no labelled data. A custom single-class
model is milestone 2 and requires a dataset that does not exist yet — the repo contains no
golf-ball imagery at all. With a fine-tuned model, pass `--coco-class -1` to disable the
filter, since a single-class model has no class 32.

**Gotchas (hard-won, keep):**
- **Windows capture backend must be DirectShow (`CAP_DSHOW`), not MSMF** — MSMF is slow to
  open and *hangs* when probing a camera index that doesn't exist. `camera.py` selects DSHOW
  on Windows, V4L2 on Linux/RP5.
- **The interactive GUI scripts (`list_cameras.py`, `calibrate.py`, `tune.py`) must be run in
  the user's own terminal** (suggest the `!` prefix), never launched by the agent in the
  background — a backgrounded process has no interactive desktop, so its OpenCV window never
  receives keystrokes and the tool aborts.
- White-ball detection is lighting-sensitive; prefer `calibrate.py` over hand-tuning, and
  re-calibrate when lighting changes. Calibrate at the distance the robot actually sees balls
  from — boxing balls held close to the camera sets a `min_area` floor that silently rejects
  everything on the far half of the green.
- **Distant balls are hard for YOLO too**, not just for the classical gates: at `--imgsz 640`
  a 720p frame is halved, so a 15 px ball lands near the stride-8 head's limit. Raise
  `--imgsz`, or let the scan → navigate loop drive closer and re-scan (preferred; no model
  change).
- **USB webcam ⇒ `cv2.VideoCapture` is the portable path.** If the team ever switches to the
  RP5 **CSI camera module**, that needs Picamera2/libcamera instead — only the capture call
  changes, `detect_golf_balls()` does not.

## Team context

Four-member team: Will (lead), Micah (computer/software — the primary user here), Tiffany (research/docs), Isaac (hardware). Software and CV work is Micah's lane; KiCad electronics is a shared learning effort.
