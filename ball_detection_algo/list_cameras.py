"""Find which camera index is the USB webcam (vs. the laptop's built-in camera).

OpenCV addresses cameras by number, and the USB cam's index varies per machine
(often 0 or 1 on a laptop; typically 0 on the RP5 when it's the only camera).

This shows a LIVE preview of each working camera, one at a time. Look at the
video, and when you see the USB webcam's view, note the index shown in the
window title/overlay. Then pass it as `--camera N` to the other scripts.

Controls (while a preview is showing):
    n  -> next camera
    q  -> quit

Usage:
    python list_cameras.py            # live-preview each camera, indices 0..5
    python list_cameras.py --max 8    # probe indices 0..8
    python list_cameras.py --no-show  # just print which indices open (headless)
"""

from __future__ import annotations

import os

# Silence OpenCV's videoio WARN spam: probing camera indices that don't exist is
# expected here, and each miss otherwise prints a scary-looking backend warning.
# Must be set before cv2 is imported (including via `camera` below).
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import argparse

import cv2

from camera import _preferred_backend

WINDOW = "camera preview  (n = next, q = quit)"


def _open(index: int, backend: int) -> cv2.VideoCapture | None:
    """Open an index and confirm it actually delivers a frame, else None."""
    cap = cv2.VideoCapture(index, backend)
    if cap.isOpened():
        ok, _ = cap.read()
        if ok:
            return cap
    cap.release()
    return None


def preview_each(max_index: int) -> list[int]:
    """Live-preview each working camera in turn. Returns working indices."""
    backend = _preferred_backend()
    working: list[int] = []
    consecutive_misses = 0
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    for index in range(max_index + 1):
        cap = _open(index, backend)
        if cap is None:
            consecutive_misses += 1
            # Camera indices are contiguous from 0; a run of misses means we're done.
            if consecutive_misses >= 3 and working:
                break
            continue
        consecutive_misses = 0
        working.append(index)
        print(f"index {index}: live preview (press n for next, q to quit)")

        quit_all = False
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            h, w = frame.shape[:2]
            cv2.putText(frame, f"index {index}   {w}x{h}   n=next  q=quit",
                        (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("n"):
                break
            if key == ord("q"):
                quit_all = True
                break
        cap.release()
        if quit_all:
            break

    cv2.destroyAllWindows()
    for _ in range(4):  # pump the GUI so the window actually closes on Windows
        cv2.waitKey(1)
    return working


def list_only(max_index: int) -> list[int]:
    """Headless: open each index, report which deliver frames, no windows."""
    backend = _preferred_backend()
    working: list[int] = []
    consecutive_misses = 0
    for index in range(max_index + 1):
        cap = _open(index, backend)
        if cap is None:
            consecutive_misses += 1
            if consecutive_misses >= 3 and working:
                break
            print(f"index {index}: not available")
            continue
        consecutive_misses = 0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"index {index}: OPEN, frame {w}x{h}")
        working.append(index)
        cap.release()
    return working


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=5, help="highest index to probe")
    parser.add_argument("--no-show", dest="show", action="store_false",
                        help="don't open preview windows (just list working indices)")
    args = parser.parse_args()

    working = preview_each(args.max) if args.show else list_only(args.max)

    if working:
        print(f"\nWorking camera indices: {working}")
        print("Use the index whose preview showed the USB webcam:")
        print("    python run_webcam.py --camera <N>")
    else:
        print("\nNo cameras opened. Is the USB webcam plugged in and not in use by another app?")


if __name__ == "__main__":
    main()
