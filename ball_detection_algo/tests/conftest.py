"""Make the flat ball_detection_algo modules importable from tests/.

The scripts import each other as top-level modules (`from detector import ...`)
because they are run from inside ball_detection_algo/, so tests need that
directory on sys.path too.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
