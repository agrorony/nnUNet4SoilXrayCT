"""Tortuosity on subvolumes (thin wrapper around the EXISTING implementation).

Calls ``tortuosity_diffusive`` from 05_evaluation/psd/psd_topology_metrics.py
(-> porespy.simulations.tortuosity_fd, default solver). New code here is only:
cube extraction, spanning-path pre-check, batching/timeouts, output collection.

Usage:
  python run_tortuosity_subvolumes.py --mode pilot
  python run_tortuosity_subvolumes.py --mode full --size 200 --max-cubes 8 --timeout 3600
"""
import argparse, json, multiprocessing as mp, os, sys, time, warnings
from pathlib import Path
import numpy as np
import scipy.ndimage as ndi

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RB = REPO.parent                      # "remote_computer backup"
sys.path.insert(0, str(REPO / "05_evaluation" / "psd"))

R = RB / "nnUNet_resources"
P = REPO / "05_evaluation/psd/pom_analysis_20260829_roi_expansion/pipeline_work"
# key: (soil, specimen, path, pore_label, voxel_um_note, circular_container)
VOLUMES = {
    "bnei_reem_specA_unified": ("Vertisol", R / "bnei_reem_specA_unified/inference_concatenated/bnei_reem_specA_unified.nii.gz", 5, False),
    "bnei_reem_specB_unified": ("Vertisol", R / "bnei_reem_specB_unified/inference_concatenated/bnei_reem_specB_unified.nii.gz", 5, False),
    "mishmar_3_5p85um_label_ds15": ("Loess", P / "mishmar_native_5p85um/mishmar_native_5p85um_label_downsample.nii.gz", 5, False),
    "mishmar_2_8p8um_label_ds15": ("Loess", P / "mishmar_second_8p8um/mishmar_second_8p8um_label_downsample.nii.gz", 5, True),
    "Cu011_samp_2": ("Loess", R / "mishmar_hanegev_Cu011_samp_2_Rec_nlm/inference_output_concat_loess_i2/mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz", 5, False),
    "Rehovot_samp2_highkV_Cu0.11_15um": ("Sand", RB / "10.5/rehovot_samp_2.npy", 1, False),
    "Rehovot_samp3_highkV_Cu0.11_15um": ("Sand", RB / "10.5/Rehovot_samp3_highkV_Cu0.11_15um.npy", 1, False),
}
SOIL_ORDER = ["Vertisol", "Loess", "Sand"]


def load_pore(path, label):
    if str(path).endswith(".npy"):
        a = np.load(path)
        return a.astype(bool) if a.dtype == bool else (a == label)
    import nibabel as nib
    return np.asarray(nib.load(str(path)).dataobj) == label


def grid_origins(shape, s, circular):
    """Non-overlapping tiling grid, centred in the volume."""
    axes = []
    for n in shape:
        k = n // s
        off = (n - k * s) // 2
        axes.append([off + i * s for i in range(k)])
    out = []
    for x in axes[0]:
        for y in axes[1]:
            for z in axes[2]:
                if circular:  # exclude cubes whose xy corners leave the inscribed sample disk
                    cx, cy = shape[0] / 2, shape[1] / 2
                    r = 0.90 * min(cx, cy)
                    cs = [(x + dx - cx, y + dy - cy) for dx in (0, s) for dy in (0, s)]
                    if max(np.hypot(*c) for c in cs) > r:
                        continue
                out.append((x, y, z))
    return out


def spanning(cube):
    """6-connectivity (scipy default 3-D structure) cluster touching both opposite faces."""
    lab, n = ndi.label(cube)
    res = []
    for ax in range(3):
        a = np.take(lab, 0, axis=ax); b = np.take(lab, -1, axis=ax)
        common = np.intersect1d(np.unique(a[a > 0]), np.unique(b[b > 0]))
        res.append(bool(common.size))
    return res


def _solve(task, q):
    """Worker: existing function, exceptions/warnings captured."""
    t0 = time.perf_counter()
    import logging
    class _H(logging.Handler):
        def __init__(self): super().__init__(); self.msgs = []
        def emit(self, rec): self.msgs.append(rec.getMessage())
    _h = _H(); logging.getLogger().addHandler(_h); logging.getLogger("porespy").addHandler(_h)
    try:
        cube = np.load(task["cube_file"])
        ax = task["axis"]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            if task["phase"] == "original":
                import psd_topology_metrics as m
                val = m.tortuosity_diffusive(cube, axes=(ax,))[f"tortuosity_axis{ax}"]
                msg = "; ".join(str(x.message) for x in w if "tortuosity_fd failed" in str(x.message))
            else:  # retry: same porespy function, documented `solver` argument
                import openpnm as op, porespy
                msg = ""
                try:
                    val = float(porespy.simulations.tortuosity_fd(
                        cube, axis=ax, solver=op.solvers.PyamgRugeStubenSolver(tol=1e-6, maxiter=5000)).tortuosity)
                except Exception as e:
                    val, msg = float("nan"), f"tortuosity_fd failed for axis={ax}: {e}"
        mm = [m for m in _h.msgs if "rates don't match" in m]
        if mm and np.isfinite(val): msg = (msg + " " if msg else "") + "FLOW_MISMATCH: " + mm[0]
        q.put((val, msg, time.perf_counter() - t0))
    except BaseException as e:
        q.put((float("nan"), f"WORKER_ERROR {type(e).__name__}: {e}", time.perf_counter() - t0))


def classify(val, msg):
    if np.isfinite(val):
        return "ok"
    if "Solver failed to converge" in msg:
        return "nonconvergence"
    return "error"


def run_tasks(tasks, timeout, nworkers):
    ctx = mp.get_context("spawn")
    pending, running, results = list(tasks), [], {}
    while pending or running:
        while pending and len(running) < nworkers:
            t = pending.pop(0)
            q = ctx.Queue(); p = ctx.Process(target=_solve, args=(t, q)); p.start()
            running.append((t, p, q, time.time()))
        time.sleep(1)
        for item in running[:]:
            t, p, q, t0 = item
            key = t["key"]
            if not q.empty():
                val, msg, rt = q.get(); p.join()
                results[key] = (classify(val, msg), val, rt, msg); running.remove(item)
            elif not p.is_alive():
                p.join()
                results[key] = ("error", float("nan"), time.time() - t0, f"process died exitcode={p.exitcode} (hard crash)")
                running.remove(item)
            elif timeout and time.time() - t0 > timeout:
                p.terminate(); p.join()
                results[key] = ("timeout", float("nan"), time.time() - t0, f"timeout>{timeout}s"); running.remove(item)
        print(f"  [{time.strftime('%H:%M:%S')}] done {len(results)}/{len(tasks)} running {len(running)}", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pilot", "full"], required=True)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--max-cubes", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--volumes", nargs="*", default=None)
    ap.add_argument("--tag", default="")
    ap.add_argument("--no-retry", action="store_true")
    a = ap.parse_args()

    out = HERE / "work"; (out / "cubes").mkdir(parents=True, exist_ok=True)
    keys = a.volumes or list(VOLUMES)
    if a.mode == "pilot":
        keys = ["bnei_reem_specA_unified", "Rehovot_samp2_highkV_Cu0.11_15um"]
    rows, tasks = [], []
    for vk in keys:
        soil, path, label, circ = VOLUMES[vk]
        vol = load_pore(path, label)
        cands = grid_origins(vol.shape, a.size, circ)
        sel = [cands[i] for i in np.unique(np.linspace(0, len(cands) - 1, min(a.max_cubes, len(cands))).round().astype(int))]
        if a.mode == "pilot":
            sel = [cands[len(cands) // 2]]  # central grid cube
        print(f"{vk}: shape {vol.shape}, {len(cands)} candidate cubes, using {len(sel)}", flush=True)
        for ci, (x, y, z) in enumerate(sel):
            cube = np.ascontiguousarray(vol[x:x+a.size, y:y+a.size, z:z+a.size])
            f = out / "cubes" / f"{vk}_s{a.size}_c{ci}.npy"; np.save(f, cube)
            span = spanning(cube); por = float(cube.mean())
            for ax in range(3):
                r = dict(soil=soil, specimen=vk, input_path=str(path), pore_label=label, cube_index=ci,
                         origin_xyz=f"{x},{y},{z}", cube_size=a.size, axis=ax, porosity=por,
                         spanning="y" if span[ax] else "n", phase="original", status="", tortuosity=np.nan,
                         runtime_s=np.nan, message="",
                         solver_settings="porespy3.0.4 tortuosity_fd default: openpnm3.6.3 PyamgRugeStubenSolver(tol=1e-8,maxiter=1000)")
                if span[ax]:
                    tasks.append(dict(key=(vk, ci, ax), cube_file=str(f), axis=ax, phase="original"))
                else:
                    r["status"] = "no_spanning_path"
                rows.append(r)
        del vol
    idx = {(r["specimen"], r["cube_index"], r["axis"]): r for r in rows}
    print(f"{len(rows)} cube-axis rows, {len(tasks)} solves", flush=True)
    res = run_tasks(tasks, a.timeout, 1 if a.mode == "pilot" else a.workers)
    for k, (st, v, rt, msg) in res.items():
        idx[k].update(status=st, tortuosity=v, runtime_s=rt, message=msg)

    retry_rows = []
    if a.mode == "full" and not a.no_retry:
        rt_tasks = [dict(key=k, cube_file=str(out / "cubes" / f"{k[0]}_s{a.size}_c{k[1]}.npy"), axis=k[2], phase="retry")
                    for k, r in idx.items() if r["status"] == "nonconvergence"]
        print(f"retry (once) for {len(rt_tasks)} nonconvergence cases", flush=True)
        rres = run_tasks(rt_tasks, a.timeout, a.workers)
        for k, (st, v, rt, msg) in rres.items():
            r = dict(idx[k]); r.update(phase="retry", status=st, tortuosity=v, runtime_s=rt, message=msg,
                                       solver_settings="RETRY: PyamgRugeStubenSolver(tol=1e-6,maxiter=5000) via tortuosity_fd(solver=...)")
            retry_rows.append(r)
    import pandas as pd
    df = pd.DataFrame(rows + retry_rows)
    df.to_csv(out / f"raw_{a.mode}{a.tag}_s{a.size}.csv", index=False)
    print(df.groupby(["soil", "status"]).size())
    if a.mode == "pilot":
        print(df[["specimen", "axis", "porosity", "spanning", "status", "tortuosity", "runtime_s", "message"]])


if __name__ == "__main__":
    main()
