"""Part D5 (approved at Gate D, Rony, 2026-11-14): record that the "canonical" Vertisol volume is specimen B.

Edits, each an exact string that must occur once (else nothing is written):
  repo:    DATA_CATALOG.md, README.md, docs/HANDOFF_REPORT.md (flag 4)
  package: 01_volumes/bnei_reem_fresh_bnei_reem_i4/README.md, 01_volumes/bnei_reem_specB_unified/README.md, README.md
Package READMEs are backed up to <backup_dir>/<same relative path> first (the repo files are in git).
Line endings are preserved. A log goes to <evidence_dir>/D5_log.json.

Usage: python d5_record_canonical_identity.py <repo_dir> <package_dir> <backup_dir> <evidence_dir>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

DATE = '2026-11-14'
WORDING = ("Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026). "
           "Source of all Vertisol POM results.")
VOXEL = ("The 0.23 % voxel-size difference (15.000149 vs 15.034357 µm) is negligible for the reported metrics, "
         "which are not recomputed.")
EVID = ("canonical's model input vs `bnei_reem_specB_unified`'s: r = 0.999929 at zero crop offset (best of 48 axis "
        "transforms × all offsets; next-best transform 0.357); vs `bnei_reem_specA_unified`'s: best r = 0.140 over all "
        "transforms and offsets. The samp_2.0 `_Rec` reconstruction (804 slices, 15.034357 µm, log `Data Directory="
        "\\\\HIVE3065\\Yael_Mishael\\Rony\\18.12.25 bnei_reem_samp_2.0`) is dated 2025-12-23, before canonical's "
        "`10.5\\nlm_volume.tif` (2026-04-20); no samp_2 reconstruction existed before 2026-08-25, and the two raw "
        "folders are separate scans (projections 12:11–13:36 vs 13:57–15:22 on 2025-12-18, all compared projections differ)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def main():
    repo, pkg, bak, evid = map(Path, sys.argv[1:5])
    cat = read(repo / 'DATA_CATALOG.md')
    nl = '\r\n' if '\r\n' in cat else '\n'

    # --- DATA_CATALOG.md: move the legacy canonical block from Specimen A to Specimen B, rewritten
    start = cat.index('**Legacy run — `bnei_reem_fresh_bnei_reem_i4` ("canonical"')
    end_marker = '\\inference_concatenated\\nlm_volume.nii.gz` |'
    end = cat.index(end_marker, start) + len(end_marker)
    old_block = cat[start:end]
    assert cat.count(old_block) == 1 and old_block.count('| Location |') == 1
    new_block = nl.join([
        f'**Legacy run — `bnei_reem_fresh_bnei_reem_i4` ("canonical", April 2026 processing) — Specimen B (resolved {DATE}); SUPERSEDED for Track E**',
        '| | |', '|---|---|',
        '| Sample ID | `bnei_reem_fresh_bnei_reem_i4` |',
        f'| Specimen | {WORDING} |',
        f'| Voxel size | **15.034357 µm** (Specimen B\'s scan log). The 15.000149 µm recorded here before {DATE} never came from a log of this volume\'s own reconstruction and is withdrawn. {VOXEL} |',
        '| Pore % / POM % | 21.636 / 0.819 |',
        '| Track E (superseded) | χ +10,318; Γ 0.859; DA 0.098; r* none in 2–537 µm |',
        '| Status | Still the source of every POM/3-class Bnei Re\'em result to date (Track A/B). **Its Track E numbers are superseded by the unified runs** (same core: `bnei_reem_specB_unified`). |',
        '| Location | `Z:\\Rony\\remote_computer backup\\nnUNet_resources\\bnei_reem_fresh_bnei_reem_i4\\inference_concatenated\\nlm_volume.nii.gz` |',
    ])
    # remove from Specimen A (with the blank line that follows it)
    assert cat[end:end + 2 * len(nl)] == nl * 2, repr(cat[end:end + 6])
    cat = cat[:start] + cat[end + 2 * len(nl):]
    # insert after Specimen B's current-run Location row
    anchor = 'run dir `Topology_Metrics_Aug2026\\raw\\psd_diag_20260907T122221_bnei_reem_specB_unified` |'
    assert cat.count(anchor) == 1
    cat = cat.replace(anchor, anchor + nl + nl + new_block)

    reps_cat = [
        # the 2026-08-29 voxel-size argument: keep, add a withdrawal note
        ("So the `samp_2` (no dot) raw core was processed twice, years apart — once as \"canonical,\" once as this week's redo — while `samp_2.0` is the other, separate physical core.",
         "So the `samp_2` (no dot) raw core was processed twice, years apart — once as \"canonical,\" once as this week's redo — while `samp_2.0` is the other, separate physical core."
         + nl + '>' + nl +
         f"> **{DATE} — the voxel-size argument above is withdrawn.** Canonical is Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`): "
         "see the RESOLVED note under Specimen B. The 15.000149 µm recorded for canonical never came from a log of canonical's own reconstruction, "
         "so it was no evidence of where the pixels came from."),
        # the OPEN flag
        ("> **⚠ OPEN — which specimen is the legacy \"canonical\" volume actually from?**",
         f"> **✅ RESOLVED ({DATE}, hand-off follow-up Part D, approved by Rony) — canonical = Specimen B.** {WORDING} Evidence: {EVID}. "
         f"Voxel size for canonical is therefore 15.034357 µm. {VOXEL} Full record: `docs/HANDOFF_FOLLOWUP_2026-11.md` (Part D). "
         "The original flag follows, for the record."
         + nl + '>' + nl +
         "> *Original flag (2026-09-07):* **⚠ OPEN — which specimen is the legacy \"canonical\" volume actually from?**"),
        ("(see `bnei_reem_specB_visual_evidence/part0d_otsu_and_identity_check.md`)",
         "(see `docs/vertisol_specimen_investigation/evidence/part0d_otsu_and_identity_check.md`)"),
        ("Bnei Re'em POM work remains **n=1** (canonical only, subject to the labelling flag above).",
         "Bnei Re'em POM work remains **n=1** (canonical only = Specimen B, resolved above)."),
        ("## Change log" + nl,
         "## Change log" + nl +
         f"- **{DATE} (hand-off follow-up, Part D):** the legacy \"canonical\" volume (`bnei_reem_fresh_bnei_reem_i4`) resolved as "
         "**Specimen B** (raw core `18.12.25 bnei_reem_samp_2.0`, 15.034357 µm); ⚠ OPEN flag replaced by the resolution; its block moved from "
         "Specimen A to Specimen B; the 2026-08-29 voxel-size argument marked withdrawn. Evidence in `docs/HANDOFF_FOLLOWUP_2026-11.md`." + nl),
    ]

    readme = read(repo / 'README.md')
    reps_readme = [
        ("| `bnei_reem_fresh_bnei_reem_i4` (\"canonical\") | Vertisol: an older processing of a scan numerically identical to specimen B (see `DATA_CATALOG.md`) | see catalog | nnU-Net `fresh_bnei_reem_i4` | source of all Vertisol POM results |",
         "| `bnei_reem_fresh_bnei_reem_i4` (\"canonical\") | Vertisol, specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026) | 15.034357 | nnU-Net `fresh_bnei_reem_i4` | source of all Vertisol POM results |"),
        ("- **Vertisol \"canonical\" volume.** It is numerically identical to specimen B, and every Vertisol POM result comes from it.",
         f"- **Vertisol \"canonical\" volume.** {WORDING} Resolved {DATE} (`DATA_CATALOG.md`, `docs/HANDOFF_FOLLOWUP_2026-11.md`). "
         f"Vertisol POM is therefore n = 1 (specimen B only). {VOXEL}"),
    ]

    rep = read(repo / 'docs/HANDOFF_REPORT.md')
    reps_rep = [
        ("4. Vertisol \"canonical\" specimen label is still unresolved; every Vertisol POM result depends on it.",
         "4. Vertisol \"canonical\" specimen label is still unresolved; every Vertisol POM result depends on it."
         f" **Resolved in the follow-up ({DATE}):** {WORDING} See `docs/HANDOFF_FOLLOWUP_2026-11.md`, Part D."),
    ]

    can_rel = '01_volumes/bnei_reem_fresh_bnei_reem_i4/README.md'
    b_rel = '01_volumes/bnei_reem_specB_unified/README.md'
    pk = {can_rel: read(pkg / can_rel), b_rel: read(pkg / b_rel), 'README.md': read(pkg / 'README.md')}
    reps_pkg = {
        can_rel: [
            ("Soil: Vertisol, Bnei Re'em. **Physical specimen: unresolved.** Its voxel size (15.000149 µm) matches specimen A's raw log, but its content is numerically identical to specimen B (`DATA_CATALOG.md`: r = 0.999929, pore Dice 0.988 against `bnei_reem_specB_unified`). This package does not call it A or B.",
             f"Soil: Vertisol, Bnei Re'em. **Physical specimen: {WORDING}** Resolved {DATE} (hand-off follow-up, Part D): {EVID}. "
             "The 15.000149 µm voxel size recorded for this volume earlier (it matches specimen A's raw log) did not come from a log of this volume's own reconstruction and is withdrawn."),
            ("Raw reconstruction this volume was cropped from: **NOT FOUND** (`DATA_CATALOG.md`: the search for canonical's own raw reconstruction came back empty). Voxel size **15.000149 µm** as recorded for this volume in `DATA_CATALOG.md` and passed to every analysis run",
             "Raw reconstruction this volume was cropped from: specimen B's `\\\\HIVE3065\\Yael_Mishael\\Rony\\18.12.25 bnei_reem_samp_2.0\\bnei_reem_highkV_cu011_samp_2.0_Rec` "
             f"(the only Bnei Re'em reconstruction that existed before this volume's 2026-04-20 file date; identified by content, {DATE}). Crop position and preprocessing log: NOT FOUND. "
             f"Voxel size **15.034357 µm** (specimen B's scan log; see `../bnei_reem_specB_unified/scan_log/`). {VOXEL} "
             "Before 2026-11-14 the voxel size was recorded as 15.000149 µm in `DATA_CATALOG.md` and passed to every analysis run"),
            ("- Specimen label unresolved (see above). Every Vertisol POM result may describe specimen B rather than A.",
             f"- Specimen B (resolved {DATE}, see above); every Vertisol POM result describes specimen B. Analysis runs used 15.000149 µm; {VOXEL[0].lower() + VOXEL[1:]}"),
        ],
        b_rel: [
            ("which is why the canonical volume's specimen label is unresolved.",
             f"because the canonical volume is a legacy (April 2026) processing of this same specimen B scan (resolved {DATE}, hand-off follow-up Part D)."),
        ],
        'README.md': [
            ("| `bnei_reem_fresh_bnei_reem_i4` (\"canonical\") | Vertisol; specimen label unresolved (numerically identical to specimen B) | 15.000149 |",
             "| `bnei_reem_fresh_bnei_reem_i4` (\"canonical\") | Vertisol, specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026) | 15.034357 |"),
            ("- **Vertisol \"canonical\" volume:** its specimen label (A or B) is unresolved, it is numerically identical to specimen B, and every Vertisol POM result comes from it.",
             f"- **Vertisol \"canonical\" volume:** {WORDING} Resolved {DATE} (see its README). {VOXEL}"),
        ],
    }

    def apply(s, reps, name):
        for old, new in reps:
            n = s.count(old)
            assert n == 1, f'{name}: expected 1 match, found {n}: {old[:90]}'
            s = s.replace(old, new)
        return s

    out = {repo / 'DATA_CATALOG.md': apply(cat, reps_cat, 'DATA_CATALOG.md'),
           repo / 'README.md': apply(readme, reps_readme, 'README.md'),
           repo / 'docs/HANDOFF_REPORT.md': apply(rep, reps_rep, 'HANDOFF_REPORT.md')}
    pkg_out = {rel: apply(s, reps_pkg[rel], rel) for rel, s in pk.items()}

    log = dict(date=DATE, repo=[], package=[])
    for p, s in out.items():
        before = sha(p); write(p, s)
        log['repo'].append(dict(path=str(p.relative_to(repo)), sha256_before=before, sha256_after=sha(p)))
    for rel, s in pkg_out.items():
        p = pkg / rel; b = bak / rel
        assert not b.exists(), f'backup {b} exists; refusing to overwrite'
        b.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, b)
        before = sha(p); write(p, s)
        log['package'].append(dict(path=rel, sha256_before=before, sha256_after=sha(p), backup=str(b)))
    json.dump(log, open(evid / 'D5_log.json', 'w'), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == '__main__':
    main()
