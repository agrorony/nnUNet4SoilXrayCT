"""Launch micro-SAM proofreader on nlm_volume (iter03 prediction + GT annotations).

Usage:
    python dev/_launch_nlm.py                         # full 652-slice volume
    python dev/_launch_nlm.py --zrange 413 433        # 20-slice crop for fast testing
    python dev/_launch_nlm.py --zrange 413 433 --no-gt
    python dev/_launch_nlm.py --zrange 413 433 --debug
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
VOL  = BASE + r"\10.5\nlm_volume.tif"
PRED = BASE + r"\nnUNet_resources\bnei_reem_iter03\inference_concatenated\nlm_volume.nii.gz"
GT   = BASE + r"\nnUNet_resources\multi_sample_iter02\_multi_sample_stage\annotations\nlm_volume.tif"

parser = argparse.ArgumentParser(description="Launch micro-SAM on nlm_volume.")
parser.add_argument("--zrange", nargs=2, type=int, metavar=("Z0", "Z1"),
                    help="Crop to Z-slice range [Z0, Z1) for quick testing")
parser.add_argument("--no-gt", action="store_true",
                    help="Skip the GT layer (faster load, no error map)")
parser.add_argument("--debug", action="store_true",
                    help="Enable debug timing/RAM logging")
args = parser.parse_args()

from run import main
main(
    VOL, PRED,
    gt_path=None if args.no_gt else GT,
    zrange=tuple(args.zrange) if args.zrange else None,
    debug=args.debug,
)
