"""Run the detector on a still image (no camera needed).

Great for offline testing and regression checks: save a photo (or a frame grab)
of golf balls on the green, run it through here, and confirm the boxes land on
the balls. Because detect_golf_balls() is a pure function, this exercises the
exact same detection code the live loop uses.

Usage:
    python test_image.py balls.jpg                 # show annotated result in a window
    python test_image.py balls.jpg -o out.jpg      # also save the annotated result
    python test_image.py balls.jpg --no-show -o out.jpg   # headless: save only
"""

from __future__ import annotations

import argparse
import sys

import cv2

from detector import DetectorParams, detect_golf_balls, draw_detections


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="path to an image file")
    parser.add_argument("-o", "--out", default=None, help="save the annotated image here")
    parser.add_argument("--no-show", dest="show", action="store_false",
                        help="don't open a window (headless)")
    args = parser.parse_args()

    frame = cv2.imread(args.image)
    if frame is None:
        print(f"Could not read image: {args.image}", file=sys.stderr)
        sys.exit(1)

    detections = detect_golf_balls(frame, DetectorParams())
    annotated = draw_detections(frame, detections)

    print(f"Detected {len(detections)} ball(s):")
    for i, d in enumerate(detections, 1):
        print(f"  {i}: box=({d.x},{d.y},{d.w},{d.h}) center={d.center} circularity={d.circularity:.2f}")

    if args.out:
        cv2.imwrite(args.out, annotated)
        print(f"Saved annotated image to {args.out}")

    if args.show:
        cv2.imshow("test_image (press any key to close)", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
