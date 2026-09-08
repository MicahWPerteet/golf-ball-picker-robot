"""Portable USB webcam access.

`cv2.VideoCapture(index)` works the same on the Windows dev laptop and on the
Raspberry Pi 5 (Linux/V4L2), so this is the code path that ships to the robot
UNCHANGED. Only the capture *backend* differs per OS, and we pick it here.

NOTE: this is for a USB (UVC) webcam. If the team later switches to the official
Raspberry Pi CSI camera module, that uses libcamera/Picamera2 instead and would
need a different opener — see README.
"""

from __future__ import annotations

import sys

import cv2


def _preferred_backend() -> int:
    """Pick the most reliable capture backend for the current OS.

    On Windows we use DirectShow (DSHOW): for USB (UVC) webcams it opens faster
    and, unlike MSMF, doesn't hang when probing a camera index that isn't there.
    """
    if sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    if sys.platform.startswith("linux"):
        # V4L2 is what the Raspberry Pi 5 uses for USB webcams.
        return cv2.CAP_V4L2
    return cv2.CAP_ANY


def open_camera(index: int, width: int = 1280, height: int = 720,
                fourcc: str = "MJPG") -> cv2.VideoCapture:
    """Open camera `index` and configure it for a fast USB stream.

    Requests MJPG so USB webcams can deliver higher resolutions at usable frame
    rates (raw YUYV is bandwidth-limited over USB). Falls back to CAP_ANY if the
    preferred backend can't open the device.

    Raises RuntimeError if the camera cannot be opened.
    """
    backend = _preferred_backend()
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        # Retry with the platform-agnostic backend before giving up.
        cap.release()
        cap = cv2.VideoCapture(index, cv2.CAP_ANY)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {index}. "
            f"Run 'python list_cameras.py' to find the USB webcam's index."
        )

    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap
