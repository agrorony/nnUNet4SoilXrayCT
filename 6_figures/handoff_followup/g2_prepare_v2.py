"""Part G prep: apply the approved package changes before Gate G (nothing deleted, everything logged).

1. Gate A (approved 2026-11-10): move A-1/A-2 (blank napari screenshots) and A-3 (zero-byte _terminal_probe.txt) to
   <removed_dir>/<same relative path>; add a one-line README.md to the two 8.8 µm Track E run folders (A-4, A-5);
   note the removal in the specB visual-evidence README that describes the screenshots.
2. Top-level README: 07_lab_data_and_writeup/ is no longer a placeholder (Part E).
3. Repo paths in the package README.md files -> the 2026-11 layout (archive/PATH_MAP_2026-11.csv), from
   G1_repo_path_citations.json (exact backticked tokens) plus a few hand-written directory cases.
   Historical reports copied into the package (anything not named README.md) are left as they are.

READMEs are backed up to <backup_dir>/<same relative path> before editing; every replacement must match.
Usage: python g2_prepare_v2.py <package_dir> <removed_dir> <backup_dir> <evidence_dir>
"""
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

TE = '05_analysis_outputs/connectivity/Topology_Metrics_Aug2026'
MOVES = [f'{TE}/bnei_reem_specB_visual_evidence/canonical_napari_3d_screenshot.png',
         f'{TE}/bnei_reem_specB_visual_evidence/specB_napari_3d_screenshot.png',
         '06_figures/selected_outputs/mishmar_hanegev2_slice_exports/_terminal_probe.txt']
TORT = ("Tortuosity failed in this run (pyamg int32 error) and was not re-run, so `extended_tortuosity.png` here is empty; "
        "the write-up's tortuosity comes from the 200³ subvolume run (`05_analysis_outputs/tortuosity_subvolumes_20261004/`).")
NEW_READMES = {f'{TE}/raw/psd_diag_20260829T164703_mishmar_hanegev_maoz_2_8p8um_native/README.md': TORT,
               f'{TE}/raw/psd_diag_20260902T215639_mishmar_second_8p8um_label_downsample_15um/README.md': TORT}
PM_NOTE = '`archive/PATH_MAP_2026-11.csv` in the repo maps each file'

SPECIAL = {
    'README.md': [
        ("| `07_lab_data_and_writeup/` | placeholder: lab data and the write-up are not included (see its README) |",
         "| `07_lab_data_and_writeup/` | lab data behind the biology figures and Table 1: 7 raw workbooks and the scripts and printed statistics for every biology-figure number (the write-up itself is not included; see its README) |"),
        ("| Lab data and the write-up | see `07_lab_data_and_writeup/README.md` |",
         "| The write-up | not included (`07_lab_data_and_writeup/README.md`) |"),
        ("references in the repository's `RESOURCES.md`", "references in the repository's `docs/RESOURCES.md` and `docs/literature/REFERENCES.md`"),
    ],
    '03_models/bnei_reem_i4/README.md': [
        ("copied from `03_training/run_configs/`; reconstructed during the 2026-07 reorg and not re-run, see `VERIFIED.md` in the code archive)",
         "copied from the repo's `3_training/vertisol_i4/`; reconstructed during the 2026-07 reorg and not re-run, see `3_training/run_configs_VERIFIED.md`)"),
    ],
    '03_models/mishmar_loess_i2/README.md': [
        ("copied from `03_training/run_configs/`; reconstructed during the 2026-07 reorg and not re-run, see `VERIFIED.md` in the code archive)",
         "copied from the repo's `3_training/loess_i2/`; reconstructed during the 2026-07 reorg and not re-run, see `3_training/run_configs_VERIFIED.md`)"),
    ],
    '05_analysis_outputs/README.md': [
        ("agent sessions; see `00_docs/prompts/` |",
         "agent sessions (their prompts, `00_docs/prompts/`, were removed from the repo in 2026-11 and are in its git history) |"),
    ],
    '06_figures/README.md': [
        ("copied from the repo's `06_reporting/` (small files only",
         f"copied from the repo's `06_reporting/` (since 2026-11 split across `6_figures/`, `3_training/training_plots/` and `archive/`; {PM_NOTE}) (small files only"),
        ("| various `06_reporting/scripts/` |", f"| various scripts formerly in `06_reporting/scripts/` ({PM_NOTE}) |"),
    ],
    '01_volumes/mishmar_hanegev_maoz_2_8p8um/README.md': [
        ("`PROJECT_STATUS.md`/ROI-expansion report", "`PROJECT_STATUS.md` (removed from the repo in 2026-11; in its git history)/ROI-expansion report"),
    ],
    f'{TE}/bnei_reem_specB_visual_evidence/README.md': [
        ("`specB_napari_3d_screenshot.png` and `canonical_napari_3d_screenshot.png` are both saved files but are **fully blank**",
         "`specB_napari_3d_screenshot.png` and `canonical_napari_3d_screenshot.png` (both removed from the v2 hand-off package, 2026-11) were saved files but were **fully blank**"),
    ],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def main():
    pkg, rem, bak, evid = map(Path, sys.argv[1:5])
    hits = json.load(open(evid / 'G1_repo_path_citations.json'))
    token_reps = defaultdict(dict)
    for h in hits:
        if not h['file'].endswith('README.md') or h['kind'] != 'file' or not h['new'] or h['new'].startswith('('):
            continue
        if h['token'] in ('DATA_CATALOG.md', 'README.md', 'RESOURCES.md') or h['token'] == h['new']:
            continue
        token_reps[h['file']][f"`{h['token']}`"] = f"`{h['new']}`"

    # plan every README edit first (all must match), then apply
    plans = {}
    for rel in sorted(set(token_reps) | set(SPECIAL)):
        p = pkg / rel
        s0 = s = read(p)
        n_tok = 0
        for old, new in SPECIAL.get(rel, []):
            assert s.count(old) == 1, f'{rel}: special match count {s.count(old)}: {old[:80]}'
            s = s.replace(old, new)
        for old, new in token_reps.get(rel, {}).items():
            c = s.count(old)
            assert c >= 1, f'{rel}: token not found {old}'
            n_tok += c
            s = s.replace(old, new)
        plans[rel] = (s0, s, n_tok)
    for rel in MOVES:
        assert (pkg / rel).is_file() and not (rem / rel).exists(), rel
    for rel in NEW_READMES:
        assert not (pkg / rel).exists(), rel

    log = dict(moved=[], added=[], edited=[])
    for rel in MOVES:
        src, dst = pkg / rel, rem / rel
        h = sha(src); n = src.stat().st_size
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        assert sha(dst) == h and not src.exists()
        log['moved'].append(dict(path=rel, to=str(dst), bytes=n, sha256=h))
    for rel, text in NEW_READMES.items():
        write(pkg / rel, text + '\r\n')
        log['added'].append(dict(path=rel, sha256=sha(pkg / rel), text=text))
    for rel, (s0, s, n_tok) in plans.items():
        p, b = pkg / rel, bak / rel
        assert not b.exists(), f'backup exists: {b}'
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, b)
        write(p, s)
        log['edited'].append(dict(path=rel, path_tokens_replaced=n_tok, special_edits=len(SPECIAL.get(rel, [])),
                                  sha256_before=sha(b), sha256_after=sha(p), backup=str(b),
                                  token_map=token_reps.get(rel, {})))
    json.dump(log, open(evid / 'G2_log.json', 'w'), indent=1, ensure_ascii=False)
    print(f"moved {len(log['moved'])}, added {len(log['added'])}, edited {len(log['edited'])} READMEs")
    for e in log['edited']:
        print(f"  {e['path']}: {e['path_tokens_replaced']} path tokens, {e['special_edits']} other edits")


if __name__ == '__main__':
    main()
