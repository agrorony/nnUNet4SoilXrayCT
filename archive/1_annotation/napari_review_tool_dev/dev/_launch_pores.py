"""Launch micro-SAM proofreader with pore GT files.

Layers:
  volume     — raw nlm_volume.tif
  prediction — less_reliable_solid_pores_GT (the annotation to be corrected)
  gt_pores   — less_reliable_solid_pores_GT reference copy
  gt_POM     — POM_GT reference

Usage:
    python dev/_launch_pores.py
    python dev/_launch_pores.py --zrange 50 70
    python dev/_launch_pores.py --zrange 50 70 --debug
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE   = r"\\HIVE3065\Yael_Mishael\Rony\remote_computer backup"
VOL    = BASE + r"\10.5\nlm_volume.tif"
PRED   = BASE + r"\nnUNet_resources\bnei_reem_iter04\inference_concatenated\nlm_volume.nii.gz"
PORES  = BASE + r"\microSAM_inputs\less_reliable_solid_pores_GT.nii.gz"
MERGED = BASE + r"\microSAM_inputs\merged_GT.nii.gz"
POM    = BASE + r"\microSAM_inputs\POM_GT.nii.gz"

parser = argparse.ArgumentParser(description="Launch micro-SAM on pore GT files.")
parser.add_argument("--zrange", nargs=2, type=int, metavar=("Z0", "Z1"),
                    help="Crop to Z-slice range [Z0, Z1)")
parser.add_argument("--debug", action="store_true",
                    help="Enable debug timing/RAM logging")
args = parser.parse_args()

from run import main
main(
    VOL,
    pred_path=PRED,                           # bnei_reem_iter04 model prediction
    extra_label_paths={"gt_pores":  PORES,     # solid pores GT reference
                       "gt_merged": MERGED,   # merged GT reference
                       "gt_POM":    POM},     # POM GT reference
    zrange=tuple(args.zrange) if args.zrange else None,
    debug=args.debug,
)
