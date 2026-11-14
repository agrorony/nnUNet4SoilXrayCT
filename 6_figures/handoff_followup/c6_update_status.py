"""Part C6 (approved at Gate C, 2026-11-10): mark the four re-verified volumes VERIFIED in the package READMEs
and copy the verification logs into each volume's provenance/.

- Backs up every README it edits to <backup_dir>/<same relative path> first (refuses to overwrite a backup).
- Every replacement must match exactly once, otherwise the script stops before writing anything.
- Logs are copied (never moved) as provenance/inference_log_verification_2026-11-10.{txt,json};
  for the samp3 Otsu mask, provenance/otsu_verification_2026-11-10.{json,txt}.
- The fresh predictions stay in _verification_2026-11/ (outside the package).

Usage: python c6_update_status.py <package_dir> <verification_dir> <evidence_dir> <backup_dir>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

DATE = '2026-11-10'
LOG = f'inference_log_verification_{DATE}'
OTSU = f'otsu_verification_{DATE}'
RUNS = ['bnei_reem_fresh_bnei_reem_i4', 'mishmar_hanegev_maoz_3_5p85um', 'mishmar_hanegev_maoz_2_8p8um']
SAMP3 = 'Rehovot_samp3_highkV_Cu0.11_15um'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt(c, lg):
    return (f"{c['voxel_agreement_pct']:.4f} % of voxels agree ({c['n_diff']:,} differ); Dice pore {c['dice_5']:.5f}, "
            f"POM {c['dice_2']:.5f}, stones {c['dice_1']:.5f}; every class fraction within {c['max_fraction_diff_pp']:.5f} "
            f"percentage points. Checkpoint `fold_0/checkpoint_final.pth`, sha256 `{lg['checkpoint']['sha256'][:12]}…` "
            f"(file date {lg['checkpoint']['mtime']}), identical to the one in `03_models/`; nnU-Net {lg['nnunetv2_version']}, "
            f"{lg['gpu'][0]}")


def main():
    pkg, ver, evid, bak = map(Path, sys.argv[1:5])
    c3 = json.load(open(evid / 'C3_results.json'))
    c4 = json.load(open(evid / 'C4_otsu.json'))[SAMP3]
    logs = {k: json.load(open(ver / k / 'inference_log.json')) for k in RUNS}
    for k in RUNS:
        assert c3[k]['packaged_vs_fresh']['status'] == 'VERIFIED (re-inference match)', k
    assert c4['fresh_from_nii_vs_packaged']['identical'] and c4['fresh_from_tif_vs_share_copy']['identical']

    def status(k):
        return f"**Verification status: VERIFIED (re-inference match, {DATE}, log: `provenance/{LOG}.txt`)**"

    def rerun(k):
        return (f"The original run left no log. On {DATE} the same model and checkpoint were re-run by the original route "
                f"(nnUNetPredictor, tile step 0.5, Gaussian weighting, no mirroring, on the original pre-split input chunks, "
                f"then `postprocessing_nnUNet_predict_concatenate.py`) into a new folder, and the fresh segmentation was compared "
                f"with this file in the same orientation: {fmt(c3[k]['packaged_vs_fresh'], logs[k])}. The few differing voxels "
                f"are GPU run-to-run noise (the fresh output is not byte-identical to the original). Command, settings, input "
                f"and output sha256 are in `provenance/{LOG}.txt` / `.json`. Evidence found before the re-run, all consistent:")

    t = c4['threshold_nii']
    edits = {
        'bnei_reem_fresh_bnei_reem_i4/README.md': [
            ("**Verification status: UNVERIFIED**. No inference log exists. Circumstantial evidence, all consistent:",
             status(0) + '. ' + rerun('bnei_reem_fresh_bnei_reem_i4')),
            ("- Inference status UNVERIFIED (no log), see above.",
             f"- The original inference left no log; verified by re-inference on {DATE} (see above)."),
        ],
        'mishmar_hanegev_maoz_3_5p85um/README.md': [
            ("**Verification status: UNVERIFIED**. No inference log exists (as already noted in `06_reporting/missing_data_20261004/REPORT.md`). Circumstantial evidence, all consistent:",
             status(0) + '. ' + rerun('mishmar_hanegev_maoz_3_5p85um').replace('The original run left no log.',
                                                                              'The original run left no log (as noted in `06_reporting/missing_data_20261004/REPORT.md`).')),
            ("Which checkpoint file (final or best) was loaded cannot be confirmed.",
             "The re-inference with `checkpoint_final.pth` reproduces the file, so the final checkpoint was the one loaded."),
            ("- Inference UNVERIFIED (no log; see above).",
             f"- The original inference left no log; verified by re-inference on {DATE} (see above)."),
        ],
        'mishmar_hanegev_maoz_2_8p8um/README.md': [
            ("**Verification status: UNVERIFIED**. No inference log exists. Circumstantial evidence, all consistent:",
             status(0) + '. ' + rerun('mishmar_hanegev_maoz_2_8p8um')),
            ("- Inference UNVERIFIED (no log).",
             f"- The original inference left no log; verified by re-inference on {DATE} (see above)."),
        ],
        f'{SAMP3}/README.md': [
            ("**Verification status: VERIFIED (nnU-Net reference outputs) / UNVERIFIED (Otsu mask)**.",
             f"**Verification status: VERIFIED (nnU-Net reference outputs) / VERIFIED (Otsu mask: re-computation match, {DATE}, log: `provenance/{OTSU}.txt`)**."),
            ("**Otsu mask UNVERIFIED:** `10.5\\Rehovot_samp3_highkV_Cu0.11_15um.npy` is dated",
             f"**Otsu mask:** on {DATE} a global Otsu threshold (`skimage.filters.threshold_otsu`, pore = voxels below it) was computed "
             f"from `10.5\\Rehovot_samp3_highkV_Cu0.11_15um.tif` (= `image_preprocessed.nii.gz`, transposed). Threshold {t:.8f}; the "
             f"resulting mask is **identical** to `segmentation_otsu.npy` (0 voxels differ; pore {c4['fresh_pore_pct']:.4f} %), in the "
             f"TIFF's own axis order identical to the share copy as well. The same check on samp2 also gives an identical mask. "
             f"So the mask content is reproducible from the image. The timestamp oddity stays unexplained: `10.5\\Rehovot_samp3_highkV_Cu0.11_15um.npy` is dated"),
            ("but the file was rewritten after the run (flag first raised in `06_reporting/missing_data_20261004/REPORT.md`).",
             "but the file was rewritten after the run (flag first raised in `06_reporting/missing_data_20261004/REPORT.md`); "
             "since a fresh Otsu mask equals it exactly, the rewrite did not change the content the run would have used."),
            ("- `segmentation_otsu.npy`: **the mask the metrics used** (UNVERIFIED timestamp, see above). True = pore.",
             f"- `segmentation_otsu.npy`: **the mask the metrics used** (content verified by re-computation {DATE}; file timestamp after the run, see above). True = pore."),
            ("- Otsu mask timestamp after the run that used it (UNVERIFIED, see above).",
             f"- Otsu mask file dated after the run that used it; content verified by re-computation on {DATE} (see above)."),
        ],
        '../README.md': [
            ("| all Vertisol POM results | **UNVERIFIED** (no inference log) |",
             f"| all Vertisol POM results | **VERIFIED** (re-inference match, {DATE}; original had no log) |"),
            ("| `mishmar_hanegev_maoz_3_5p85um` | Loess (external scan) | 5.85; ~15 µm label-downsamples | nnU-Net `…_loess_i2` | structure + POM | **UNVERIFIED** (no inference log); 15 µm Track E mask VERIFIED |",
             f"| `mishmar_hanegev_maoz_3_5p85um` | Loess (external scan) | 5.85; ~15 µm label-downsamples | nnU-Net `…_loess_i2` | structure + POM | **VERIFIED** (re-inference match, {DATE}; original had no log); 15 µm Track E mask VERIFIED |"),
            ("| `mishmar_hanegev_maoz_2_8p8um` | Loess (external scan) | 8.8; ~15 µm label-downsamples | nnU-Net `…_loess_i2` | structure + POM | **UNVERIFIED** (no inference log); 15 µm Track E mask VERIFIED |",
             f"| `mishmar_hanegev_maoz_2_8p8um` | Loess (external scan) | 8.8; ~15 µm label-downsamples | nnU-Net `…_loess_i2` | structure + POM | **VERIFIED** (re-inference match, {DATE}; original had no log); 15 µm Track E mask VERIFIED |"),
            ("| nnU-Net VERIFIED; **Otsu mask UNVERIFIED** (file dated after the run that used it) |",
             f"| nnU-Net VERIFIED; Otsu mask **VERIFIED** (re-computation match, {DATE}; file dated after the run that used it) |"),
            ("UNVERIFIED = no log. Timestamps, the copied `plans.json` (byte-identical to the claimed model's, and unique to it) and the fractions are all consistent, but which checkpoint file was loaded cannot be proven.",
             f"VERIFIED (re-inference match) = the original run left no log, so on {DATE} the same checkpoint was re-run by the original "
             f"route on the original input and the fresh segmentation matched the packaged one (≥ 99.9988 % of voxels, Dice ≥ 0.9999 for every class); "
             f"the new log is in the volume's `provenance/`. VERIFIED (re-computation match) = the Otsu mask was recomputed from its image and is identical. "
             f"No volume is UNVERIFIED any more."),
        ],
    }

    # dry pass: every old string must occur exactly once
    new_text = {}
    for rel, reps in edits.items():
        p = pkg / '01_volumes' / rel
        with open(p, encoding='utf-8', newline='') as f:
            s = f.read()  # keep the file's own line endings
        for old, new in reps:
            n = s.count(old)
            assert n == 1, f'{rel}: expected 1 match, found {n}: {old[:80]}'
            s = s.replace(old, new)
        new_text[p] = s

    # copy plan (provenance)
    copies = []
    for k in RUNS:
        for ext in ('txt', 'json'):
            copies.append((ver / k / f'inference_log.{ext}', pkg / '01_volumes' / k / 'provenance' / f'{LOG}.{ext}'))
    copies.append((evid / 'C4_otsu.json', pkg / '01_volumes' / SAMP3 / 'provenance' / f'{OTSU}.json'))
    for _, dst in copies:
        assert not dst.exists(), f'{dst} exists; refusing to overwrite'

    # back up, then write
    log = dict(date=DATE, readmes=[], copies=[])
    for p, s in new_text.items():
        rel = p.resolve().relative_to(pkg.resolve())
        b = bak / rel
        assert not b.exists(), f'backup {b} exists; refusing to overwrite'
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, b)
        assert sha(b) == sha(p)
        before = sha(p)
        with open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(s)
        log['readmes'].append(dict(path=str(rel), sha256_before=before, sha256_after=sha(p), backup=str(b)))
    for src, dst in copies:
        shutil.copy2(src, dst)
        assert sha(src) == sha(dst)
        log['copies'].append(dict(src=str(src), dst=str(dst.relative_to(pkg)), sha256=sha(dst), bytes=dst.stat().st_size))

    # readable txt log for the Otsu check
    r = c4
    txt = pkg / '01_volumes' / SAMP3 / 'provenance' / f'{OTSU}.txt'
    assert not txt.exists()
    txt.write_text(
        f"Otsu mask re-computation, {DATE} (hand-off follow-up, Part C4)\n"
        f"script: 6_figures/handoff_followup/c4_otsu_check.py (repo nnUNet4SoilXrayCT)\n"
        f"source image: {r['source_tif']}  shape {r['tif_shape']}  dtype {r['tif_dtype']}\n"
        f"image_preprocessed.nii.gz == source TIFF transposed (2,1,0): {r['tif_equals_packaged_image_transposed']}\n"
        f"method: skimage.filters.threshold_otsu on the whole volume; pore = voxel < threshold\n"
        f"threshold (TIFF): {r['threshold_tif']!r}\nthreshold (NIfTI): {r['threshold_nii']!r}\n"
        f"fresh mask vs packaged segmentation_otsu.npy: identical={r['fresh_from_nii_vs_packaged']['identical']}, "
        f"voxels differing={r['fresh_from_nii_vs_packaged']['n_diff']}, Dice={r['fresh_from_nii_vs_packaged']['dice']}\n"
        f"fresh mask (TIFF order) vs share copy 10.5\\Rehovot_samp3_highkV_Cu0.11_15um.npy (pre-flip): "
        f"identical={r['fresh_from_tif_vs_share_copy']['identical']}\n"
        f"pore fraction: packaged {r['packaged_pore_pct']:.6f} %, fresh {r['fresh_pore_pct']:.6f} %\n"
        f"control: the same check on Rehovot_samp2_highkV_Cu0.11_15um gives an identical mask as well.\n",
        encoding='utf-8')
    log['copies'].append(dict(src='generated from C4_otsu.json', dst=str(txt.relative_to(pkg)), sha256=sha(txt), bytes=txt.stat().st_size))
    json.dump(log, open(evid / 'C6_log.json', 'w'), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == '__main__':
    main()
