"""REV (representative elementary volume) check: porosity vs. nested cube size,
centered at the same point, for one soil (Bnei Re'em -- has the most headroom for
large nested cubes). Confirms whether porosity has stabilized by the chosen
subvolume edge (300 vox / 4.50mm) before trusting subvolume-level porosity as
representative.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

OUT_ROOT = Path(__file__).resolve().parents[1]

PATH = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz"
VOXEL_UM = 15.000149
PORE_LABEL = 5
SIZES = [75, 150, 225, 300, 400, 500]

vol = np.asarray(nib.load(PATH).dataobj)
pore = vol == PORE_LABEL
cz, cy, cx = (s // 2 for s in vol.shape)
print(f"volume shape {vol.shape}, center ({cz},{cy},{cx})")

rows = []
for s in SIZES:
    half = s // 2
    z0, z1 = cz - half, cz - half + s
    y0, y1 = cy - half, cy - half + s
    x0, x1 = cx - half, cx - half + s
    if z0 < 0 or y0 < 0 or x0 < 0 or z1 > vol.shape[0] or y1 > vol.shape[1] or x1 > vol.shape[2]:
        print(f"  S={s}: out of bounds, skipping")
        continue
    sub = pore[z0:z1, y0:y1, x0:x1]
    porosity = float(np.mean(sub))
    edge_mm = s * VOXEL_UM / 1000.0
    rows.append({"edge_voxels": s, "edge_mm": round(edge_mm, 4), "porosity": porosity})
    print(f"  S={s} ({edge_mm:.3f} mm): porosity={porosity:.4f}")

out_json = OUT_ROOT / "rev_check_bnei_reem.json"
with out_json.open("w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=2)

fig, ax = plt.subplots(figsize=(6, 4.5), dpi=150)
edges = [r["edge_mm"] for r in rows]
poros = [r["porosity"] for r in rows]
ax.plot(edges, poros, "o-", color="#3b7dd8", linewidth=2, markersize=7)
ax.axvline(300 * VOXEL_UM / 1000.0, color="gray", linestyle="--", alpha=0.7,
           label="chosen subvolume edge (4.50mm)")
ax.set_xlabel("Cube edge length (mm)")
ax.set_ylabel("Porosity")
ax.set_title("REV check: porosity vs. nested cube size\nBnei Re'em, centered at volume center")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(str(OUT_ROOT / "rev_check_bnei_reem.png"), dpi=200)
print(f"\nWrote {out_json} and rev_check_bnei_reem.png")

# Simple stabilization check: relative change in porosity between the last two sizes
if len(rows) >= 2:
    rel_change = abs(rows[-1]["porosity"] - rows[-2]["porosity"]) / rows[-2]["porosity"]
    print(f"Relative porosity change, last two sizes: {rel_change:.4%}")
