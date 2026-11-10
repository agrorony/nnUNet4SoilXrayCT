import json
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(OUT_ROOT / "all_soils_interface_summary.json"))
br = d["bnei_reem"]
mn = d["mishmar_native"]
m2 = d["mishmar_sample2"]


def mean_se(a, b):
    mean = (a + b) / 2.0
    se = abs(a - b) / 2.0
    return mean, se


def get(dd, keys):
    v = dd
    for k in keys:
        v = v[k]
    return v


ROWS = [
    ("POM-pore contact fraction (voxel-face)", ["part1_voxel_face_contact", "pom_pore_contact_fraction_voxel"], 1),
    ("POM-matrix contact fraction (voxel-face)", ["part1_voxel_face_contact", "pom_matrix_contact_fraction_voxel"], 1),
    ("Voxel-face overlap fraction", ["part1_voxel_face_contact", "overlap_fraction_voxel"], 1),
    ("Voxel-face neither fraction", ["part1_voxel_face_contact", "neither_fraction_voxel"], 1),
    ("MC total surface area (mm2)", ["part2_marching_cubes", "pom_surface_area_um2_marching_cubes_total"], 1e-6),
    ("Voxel-face total surface area (mm2)", ["part2_marching_cubes", "pom_surface_area_um2_voxel_face_count_total"], 1e-6),
    ("MC pore-facing area fraction", ["part2_marching_cubes", "mc_pore_area_fraction"], 1),
    ("MC matrix-facing area fraction", ["part2_marching_cubes", "mc_matrix_area_fraction"], 1),
    ("SSA total (mm2/mm3)", ["part3_ssa_iad", "ssa_total_mm2_per_mm3"], 1),
    ("SSA pore-facing (mm2/mm3)", ["part3_ssa_iad", "ssa_pore_facing_mm2_per_mm3"], 1),
    ("SSA matrix-facing (mm2/mm3)", ["part3_ssa_iad", "ssa_matrix_facing_mm2_per_mm3"], 1),
    ("IAD pore (mm2/mm3)", ["part3_ssa_iad", "iad_pore_mm2_per_mm3"], 1),
    ("IAD matrix (mm2/mm3)", ["part3_ssa_iad", "iad_matrix_mm2_per_mm3"], 1),
    ("Largest-object interface-area share (pct)", ["part4_object_level", "largest_object_interface_area_share"], 100),
    ("Top5-object interface-area share (pct)", ["part4_object_level", "top5_objects_interface_area_share"], 100),
]

header = f'{"metric":45s} {"BneiReem(n=1)":>16s} {"Mishmar mean(n=2)":>20s} {"Mishmar SE":>12s} {"native_val":>12s} {"sample2_val":>12s}'
print(header)
print("-" * len(header))
table_rows = []
for name, keys, scale in ROWS:
    bv = get(br, keys) * scale
    nv = get(mn, keys) * scale
    sv = get(m2, keys) * scale
    mean, se = mean_se(nv, sv)
    print(f"{name:45s} {bv:16.5f} {mean:20.5f} {se:12.5f} {nv:12.5f} {sv:12.5f}")
    table_rows.append((name, bv, mean, se, nv, sv))

with open(OUT_ROOT / "comparison_table_raw.json", "w", encoding="utf-8") as fh:
    json.dump(
        [dict(metric=r[0], bnei_reem=r[1], mishmar_mean=r[2], mishmar_se=r[3],
              mishmar_native=r[4], mishmar_sample2=r[5]) for r in table_rows],
        fh, indent=2,
    )
print("\nWrote comparison_table_raw.json")
