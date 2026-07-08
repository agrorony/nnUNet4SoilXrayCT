"""Comprehensive test suite for microsam_3d — no live napari window required.
Run with: C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe _test_suite.py
"""
import sys, os, json, subprocess, tempfile, time, warnings
from pathlib import Path
import numpy as np

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
MICROSAM_DIR = Path(__file__).parent.parent  # dev/ → microsam_3d/
PYTHON       = r"C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe"
BASE_HIVE    = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
RAW_PATH     = BASE_HIVE + r"\10.5\nlm_volume.tif"
GT_PATH      = (BASE_HIVE
                + r"\nnUNet_resources\multi_sample_iter02"
                + r"\_multi_sample_stage\annotations\nlm_volume.tif")
PRED_PATH    = (BASE_HIVE
                + r"\nnUNet_resources\bnei_reem_iter03"
                + r"\inference_concatenated\nlm_volume.nii.gz")
# Crop covering annotated slices at z=415-418 (in the 652-page stack)
Z0, Z1 = 413, 433

sys.path.insert(0, str(MICROSAM_DIR))

# ── Test runner ───────────────────────────────────────────────────────────────
results: list[tuple] = []

def run_test(name: str, fn):
    t0 = time.time()
    try:
        msg = fn()
        dt  = time.time() - t0
        results.append((name, "PASS", msg or "", dt))
        print(f"{name:<30} PASS  {msg or ''}")
    except Exception as exc:
        dt = time.time() - t0
        import traceback
        detail = traceback.format_exc().strip().splitlines()[-1]
        results.append((name, "FAIL", detail, dt))
        print(f"{name:<30} FAIL  {detail}")

# ── Shared context (populated by tests in order) ──────────────────────────────
ctx: dict = {}

# ─────────────────────────────────────────────────────────────────────────────
# T1 — All 5 module imports
# ─────────────────────────────────────────────────────────────────────────────
def t1():
    from embedder        import VolumeEmbedder
    from error_map       import compute_error_map
    from predictor       import MaskPredictor3D
    from correction_store import CorrectionStore
    from napari_plugin   import create_widget
    ctx["VolumeEmbedder"] = VolumeEmbedder
run_test("T1  imports", t1)

# ─────────────────────────────────────────────────────────────────────────────
# T2 — GPU
# ─────────────────────────────────────────────────────────────────────────────
def t2():
    import torch
    assert torch.cuda.is_available(), "torch.cuda.is_available() is False"
    name = torch.cuda.get_device_name(0)
    return name
run_test("T2  GPU", t2)

# ─────────────────────────────────────────────────────────────────────────────
# T3 — SAM model load (weights should be cached from earlier run)
# ─────────────────────────────────────────────────────────────────────────────
def t3():
    from micro_sam.util import get_sam_model
    t0  = time.time()
    pred = get_sam_model(model_type="vit_b")
    dt  = time.time() - t0
    import torch
    device = next(pred.model.parameters()).device
    assert str(device).startswith("cuda"), f"Expected cuda device, got {device}"
    assert dt < 15, f"Model load took {dt:.1f}s (>15s — cache miss?)"
    ctx["sam_predictor"] = pred
    return f"{dt:.1f}s  device={device}"
run_test("T3  SAM load", t3)

# ─────────────────────────────────────────────────────────────────────────────
# T4 — VolumeEmbedder: on-demand cache on real data
# ─────────────────────────────────────────────────────────────────────────────
def t4():
    import tifffile
    from embedder import VolumeEmbedder

    with tifffile.TiffFile(RAW_PATH) as tf:
        raw = np.stack([tf.pages[z].asarray() for z in range(Z0, Z1)]).astype(np.float32)
    vmin, vmax = raw.min(), raw.max()
    raw = (raw - vmin) / (vmax - vmin)
    ctx["raw"] = raw

    embedder = VolumeEmbedder(raw, model_type="vit_b")
    ctx["embedder"] = embedder

    t0 = time.time(); emb = embedder.get_embedding(5); t_first = time.time() - t0
    t0 = time.time(); embedder.get_embedding(5);        t_cache  = time.time() - t0

    assert t_first < 10,   f"First embedding {t_first:.2f}s > 10s"
    assert t_cache < 0.01, f"Cached embedding {t_cache:.5f}s > 0.01s"
    assert emb["features"].shape == (1, 256, 64, 64), \
        f"Unexpected features shape: {emb['features'].shape}"
    return f"first={t_first:.2f}s cached={t_cache:.5f}s"
run_test("T4  VolumeEmbedder", t4)

# ─────────────────────────────────────────────────────────────────────────────
# T5 — compute_error_map with GT
# ─────────────────────────────────────────────────────────────────────────────
def t5():
    import tifffile
    import nibabel as nib
    from error_map import compute_error_map

    with tifffile.TiffFile(GT_PATH) as tf:
        gt = np.stack([tf.pages[z].asarray() for z in range(Z0, Z1)])
    pred_full = np.asarray(nib.load(PRED_PATH).dataobj).T   # (Z,Y,X)
    pred = pred_full[Z0:Z1].copy()
    ctx["gt"] = gt
    ctx["pred"] = pred

    em = compute_error_map(pred, gt)
    assert em.shape == pred.shape, f"Shape mismatch: {em.shape} vs {pred.shape}"
    assert em.max() > 0, "Error map is all-zeros — no disagreement between pred and GT"
    ctx["error_map_gt"] = em
    pct = 100.0 * float(em.mean())
    return (f"shape={em.shape}  gt_unique={np.unique(gt).tolist()}  "
            f"pred_unique={np.unique(pred).tolist()}  error={pct:.1f}%")
run_test("T5  error_map GT", t5)

# ─────────────────────────────────────────────────────────────────────────────
# T6 — compute_error_map without GT (gradient proxy)
# ─────────────────────────────────────────────────────────────────────────────
def t6():
    from error_map import compute_error_map
    pred = ctx.get("pred")
    if pred is None:
        raise RuntimeError("pred not available — T5 may have failed")
    em = compute_error_map(pred)
    assert em.shape == pred.shape, f"Shape mismatch: {em.shape}"
    assert em.dtype in (np.float32, np.float64), f"Expected float dtype, got {em.dtype}"
    assert em.max() > 0, "Gradient map is all-zeros — volume appears completely flat"
    return f"shape={em.shape}  dtype={em.dtype}  max={em.max():.4f}"
run_test("T6  error_map no-GT", t6)

# ─────────────────────────────────────────────────────────────────────────────
# T7 — get_error_regions
# ─────────────────────────────────────────────────────────────────────────────
def t7():
    from error_map import get_error_regions
    em = ctx.get("error_map_gt")
    if em is None:
        raise RuntimeError("error_map_gt not available — T5 may have failed")
    regions = get_error_regions(em, min_size=500)
    assert len(regions) >= 1, "No error regions found with min_size=500"
    r = regions[0]
    assert "bbox" in r and "size" in r, f"Region dict missing keys: {set(r.keys())}"
    assert r["size"] > 0, "Largest region has size 0"
    ctx["error_regions"] = regions
    return f"{len(regions)} regions  largest: size={r['size']}  bbox={r['bbox']}"
run_test("T7  get_error_regions", t7)

# ─────────────────────────────────────────────────────────────────────────────
# T8 — MaskPredictor3D.predict_region on real data
# ─────────────────────────────────────────────────────────────────────────────
def t8():
    from predictor import MaskPredictor3D
    embedder = ctx.get("embedder")
    regions  = ctx.get("error_regions")
    if embedder is None: raise RuntimeError("embedder not available — T4 failed")
    if regions  is None: raise RuntimeError("error_regions not available — T7 failed")

    z0r, z1r, y0, y1, x0, x1 = regions[0]["bbox"]
    z1r = min(z1r, z0r + 5)                        # cap Z depth to 5 slices
    bbox = (z0r, z1r, y0, y1, x0, x1)

    cy = (y0 + y1) // 2
    cx = (x0 + x1) // 2
    point_coords = np.array([[cy, cx]])
    point_labels = np.array([1])

    pred3d = MaskPredictor3D(embedder)
    t0 = time.time()
    patch = pred3d.predict_region(bbox, point_coords, point_labels)
    dt = time.time() - t0

    expected_shape = (z1r - z0r, y1 - y0, x1 - x0)
    assert patch.shape == expected_shape, \
        f"patch.shape {patch.shape} != expected {expected_shape}"
    assert patch.dtype in (np.uint8, bool, np.bool_), \
        f"Unexpected dtype: {patch.dtype}"
    patch = patch.astype(np.uint8)
    uvals = np.unique(patch).tolist()
    assert 0 in uvals and 1 in uvals, \
        (f"Mask is uniform ({uvals}) — SAM returned a trivial all-zero or all-one mask. "
         f"bbox={bbox}  point=({cy},{cx})")
    ctx["patch"] = patch
    ctx["bbox"]  = bbox
    return f"{dt:.2f}s  shape={patch.shape}  values={uvals}"
run_test("T8  predict_region", t8)

# ─────────────────────────────────────────────────────────────────────────────
# T9 — CorrectionStore: add + export round-trip
# ─────────────────────────────────────────────────────────────────────────────
def t9():
    import tifffile as tf_
    from correction_store import CorrectionStore

    pred  = ctx.get("pred")
    raw   = ctx.get("raw")
    patch = ctx.get("patch")
    bbox  = ctx.get("bbox")
    if any(v is None for v in [pred, raw, patch, bbox]):
        raise RuntimeError("Context missing — T4/T5/T8 may have failed")

    store = CorrectionStore(pred.shape)
    store.add(bbox, patch)
    assert len(store.corrections) == 1

    corrected_shape = None
    pair_vol_shape  = None
    pair_gt_shape   = None

    with tempfile.TemporaryDirectory() as td:
        store.export(td, raw, pred)
        td_path = Path(td)
        assert (td_path / "corrected_labels.tiff").exists()
        assert (td_path / "pair_0000.npz").exists()

        corrected_shape = tf_.imread(str(td_path / "corrected_labels.tiff")).shape
        assert corrected_shape == pred.shape, \
            f"corrected shape {corrected_shape} != pred shape {pred.shape}"

        with np.load(str(td_path / "pair_0000.npz")) as pair:
            pair_vol_shape = pair["volume"].shape
            pair_gt_shape  = pair["gt"].shape

    z0r, z1r, y0, y1, x0, x1 = bbox
    exp = (z1r - z0r, y1 - y0, x1 - x0)
    assert pair_vol_shape == exp, f"volume crop {pair_vol_shape} != {exp}"
    assert pair_gt_shape  == exp, f"gt crop {pair_gt_shape} != {exp}"
    return f"corrected={corrected_shape}  pair_vol={pair_vol_shape}"
run_test("T9  CorrectionStore", t9)

# ─────────────────────────────────────────────────────────────────────────────
# T10 — load_rois_from_file (JSON)
# ─────────────────────────────────────────────────────────────────────────────
def t10():
    from napari_plugin import load_rois_from_file
    rois_data = [{"z0": 50, "z1": 55, "y0": 100, "y1": 200, "x0": 100, "x1": 200}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(rois_data, f)
        path = f.name
    try:
        loaded = load_rois_from_file(path)
    finally:
        os.unlink(path)
    assert len(loaded) == 1, f"Expected 1 ROI, got {len(loaded)}"
    r = loaded[0]
    assert r["z0"] == 50  and r["z1"] == 55
    assert r["y0"] == 100 and r["y1"] == 200
    assert r["x0"] == 100 and r["x1"] == 200
    return f"{len(loaded)} ROI loaded, keys={sorted(r.keys())}"
run_test("T10 ROI JSON load", t10)

# ─────────────────────────────────────────────────────────────────────────────
# T11 — run.py --help via subprocess
# ─────────────────────────────────────────────────────────────────────────────
def t11():
    result = subprocess.run(
        [PYTHON, str(MICROSAM_DIR / "run.py"), "--help"],
        capture_output=True, text=True, timeout=30,
        cwd=str(MICROSAM_DIR),
    )
    assert result.returncode == 0, \
        f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr[-300:]}"
    out = (result.stdout + result.stderr).lower()
    assert "volume" in out and "pred" in out, \
        f"Expected 'volume' and 'pred' in --help output:\n{result.stdout}"
    return f"exit=0"
run_test("T11 run.py --help", t11)

# ─────────────────────────────────────────────────────────────────────────────
# T12 — napari_plugin headless import (subprocess, no Qt app)
# ─────────────────────────────────────────────────────────────────────────────
def t12():
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    result = subprocess.run(
        [PYTHON, "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from napari_plugin import create_widget; print('OK')"],
        capture_output=True, text=True, timeout=30,
        cwd=str(MICROSAM_DIR), env=env,
    )
    stderr_tail = result.stderr.strip().splitlines()
    # Filter known benign warnings
    errors = [l for l in stderr_tail
              if l and "UserWarning" not in l and "import elf" not in l
              and "FutureWarning" not in l and "DeprecationWarning" not in l]
    assert result.returncode == 0, \
        f"exit={result.returncode}\n" + "\n".join(errors[-10:])
    assert "OK" in result.stdout, f"'OK' not in stdout:\n{result.stdout}"
    return "import succeeded in fresh subprocess"
run_test("T12 napari headless", t12)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passed = sum(1 for _, s, _, _ in results if s == "PASS")
total  = len(results)
fails  = [(n, m) for n, s, m, _ in results if s == "FAIL"]

if fails:
    print("── FAILURES " + "─" * 50)
    for name, msg in fails:
        print(f"  {name}:  {msg}")
    print()

print(f"{passed}/{total} PASSED")
sys.exit(0 if passed == total else 1)
