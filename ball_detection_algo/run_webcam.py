"""Live white-golf-ball detector on the USB webcam.

Opens the camera you point it at, runs the detector on each frame, and draws a
green box around every white golf ball. This is the entry point that will run on
the Raspberry Pi 5 (add --no-display when the robot is headless).

Usage:
    python run_webcam.py --camera 1                 # laptop USB webcam
    python run_webcam.py --camera 0 --no-display    # headless RP5
    python run_webcam.py --camera 1 --save last.jpg # also save the latest annotated frame
Press 'q' in the window to quit.
"""

from __future__ import annotations

import argparse
import time

import cv2

from camera import open_camera
from detector import DetectorParams, detect_golf_balls, draw_detections


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, required=True,
                        help="camera index (find it with list_cameras.py)")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--no-display", dest="display", action="store_false",
                        help="don't open a window (headless robot)")
    parser.add_argument("--save", metavar="PATH", default=None,
                        help="write the latest annotated frame to this path each loop")
    parser.add_argument("--params", metavar="PATH", default=None,
                        help="load tuned thresholds from a JSON file (see calibrate.py)")
    args = parser.parse_args()

    params = DetectorParams.load(args.params) if args.params else DetectorParams()
    if args.params:
        print(f"Loaded params from {args.params}")
    cap = open_camera(args.camera, args.width, args.height)

    print(f"Camera {args.camera} opened. Press 'q' to quit." if args.display
          else f"Camera {args.camera} opened (headless). Ctrl-C to quit.")

    fps_t0 = time.time()
    frames = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("Dropped frame; retrying...")
                continue

            detections = detect_golf_balls(frame, params)
            annotated = draw_detections(frame, detections)

            frames += 1
            if frames % 30 == 0:
                dt = time.time() - fps_t0
                print(f"{frames / dt:.1f} FPS, {len(detections)} ball(s) this frame")
                fps_t0, frames = time.time(), 0

            if args.save:
                cv2.imwrite(args.save, annotated)

            if args.display:
                cv2.imshow("golf ball detector (press q to quit)", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
