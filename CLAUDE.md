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
- **Vision:** on-board camera + CV detection is a high-value but *not top-priority* capability (priority #4). Hardware reliability — drivetrain, collection, return-to-dock — comes first.

## Computer-vision module (`ball_detection_algo/`)

v1 detects white golf balls in a USB-webcam feed and draws a bounding box around
each. Written to run **unchanged on the RP5** (Linux/V4L2); the Windows laptop is just
the dev box. See `ball_detection_algo/README.md` for full usage.

**Design (deliberate, don't flatten it):** detection is **classical CV, not ML** — HSV
white-thresholding + morphology + contour shape-gating (area, circularity, fill-ratio).
The core is a **pure `detect_golf_balls(frame, params) -> list[Detection]`** in
`detector.py` (no camera/window/disk), so it's testable on still images and drops into the
autonomous state machine (…→ scan → navigate →…) as an isolated node. Camera capture,
tuning, and display live in separate scripts that call into it. All thresholds live in one
`DetectorParams` dataclass, which serializes to/from JSON (`params.json`). `params.json` is git-ignored — it is per-camera, per-lighting calibration output, so each machine generates its own with `calibrate.py`.

**Environment:** a venv lives at `ball_detection_algo/.venv`. Run scripts with
`.venv\Scripts\python.exe` (Windows) / `.venv/bin/python` (RP5). `pip install -r
requirements.txt` pulls prebuilt wheels on any Python 3.9–3.14 (OpenCV ships an abi3 wheel);
no version pin is needed despite the local Python being 3.14.

**Typical workflow:** `list_cameras.py` (find the USB cam's index — it is *not* the laptop's
built-in) → `calibrate.py --camera N` (box a few real balls; it derives thresholds and writes
`params.json`) → `run_webcam.py --camera N --params params.json`. `tune.py` is the manual
slider fallback; `test_image.py` runs the detector on a still photo.

**Gotchas (hard-won, keep):**
- **Windows capture backend must be DirectShow (`CAP_DSHOW`), not MSMF** — MSMF is slow to
  open and *hangs* when probing a camera index that doesn't exist. `camera.py` selects DSHOW
  on Windows, V4L2 on Linux/RP5.
- **The interactive GUI scripts (`list_cameras.py`, `calibrate.py`, `tune.py`) must be run in
  the user's own terminal** (suggest the `!` prefix), never launched by the agent in the
  background — a backgrounded process has no interactive desktop, so its OpenCV window never
  receives keystrokes and the tool aborts.
- White-ball detection is lighting-sensitive; prefer `calibrate.py` over hand-tuning, and
  re-calibrate when lighting changes.
- **USB webcam ⇒ `cv2.VideoCapture` is the portable path.** If the team ever switches to the
  RP5 **CSI camera module**, that needs Picamera2/libcamera instead — only the capture call
  changes, `detect_golf_balls()` does not.

## Team context

Four-member team: Will (lead), Micah (computer/software — the primary user here), Tiffany (research/docs), Isaac (hardware). Software and CV work is Micah's lane; KiCad electronics is a shared learning effort.
