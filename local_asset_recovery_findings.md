> **RESOLVED 2026-10-04:** share access restored — nothing was deleted. The access-denied findings below are historical.

# Local asset recovery check — Mishmar HaNegev models/inference

Read-only diagnostic. Nothing was deleted, moved, renamed, or rerun. Run 2026-09-21, on-machine (hostname `HIVE3065` — see §3, this machine *is* the host the codebase calls `hive3065`).

## Bottom line first

**Nothing appears to have been deleted.** The 2026-07/08 reorg (`REORG_PLAN.md`/`REORG_EXECUTION_REPORT.md`) never touched anything Mishmar-HaNegev-related — it only reorganized files inside this git repo, and nnU-Net checkpoints/training outputs were never stored in the repo or touched by it (by design — see §1). The actual blocker is an **access-permission problem on the `E:\PROJECTS\Yael_Mishael` folder** (the same folder the codebase reaches via `\\hive3065\Yael_Mishael\...` and `Z:\Rony\...`): the folder physically exists, but the current Windows account (`hive3065\rony.schwartz`) gets "Access is denied" on every attempt to list or read inside it — even though `whoami /groups` shows this account *is* a member of a group called `HIVE3065\_Yael_Mishael` that looks purpose-built to grant exactly this access (§3). This is a Windows account/ACL issue, not a storage-layer deletion, and it broke **within roughly the last hour**, not months ago (§3, timestamp evidence). Separately, and not blocking anything: the `\\hive3065\Yael_Mishael` SMB share itself no longer appears in this machine's share list, while ~70 sibling lab shares (`E:\PROJECTS\<lab>_lab`) are all still published normally.

Despite the live checkpoint/raw-volume being inaccessible right now, **Rony can already show substantial Mishmar HaNegev results** from pre-existing, git-tracked local output — POM/PSD/connectivity analysis products and rendered segmentation slice images going back to May–September 2026 (§4). What can't currently be regenerated or freshly viewed is anything needing live access to the checkpoint or raw scan (e.g. today's attempted napari session — §3).

---

## 1. What the reorg reports say (with quotes)

Both `REORG_PLAN.md` and `REORG_EXECUTION_REPORT.md` are entirely scoped to this git repository (`nnUNet4SoilXrayCT`) — moving/renaming/archiving/gitignoring files that live inside it. Neither document ever references `nnUNet_results`, `nnUNet_raw`, `nnUNet_preprocessed`, or the `\\hive3065\Yael_Mishael\...\nnUNet_resources\` tree, because — confirmed directly in `03_training/scripts/run_training.py` — training/checkpoint output has **never lived in the repo or under git**: 

> `hive_base = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'` ... `local_base = os.path.join(hive_base, f"multi_sample_{cfg['iteration_name']}")` — despite the name, `local_base` is itself a path *on the hive share*, not on local disk.

Deletions the reorg actually performed, per `REORG_EXECUTION_REPORT.md` §1–§4, were all repo-internal and none are Mishmar-specific:
- Two superseded JSON files in a registry mutation chain ("**Both superseded files deleted**; only `..._yfix.json` kept" — §2), unrelated to Mishmar.
- `.github/agents/*.agent.md` + one skill file, deleted per "amendment B" — tooling config, unrelated.
- Empty 0-byte log files and empty directories (`preprocess/nlm_output/`, `preprocess/norm200_output/`, `legacy/pores_analysis/results/`) — none Mishmar-named.
- 7 previously-committed log files were `git rm --cached` ("**archive (don't delete), no history rewrite**" — §3 table, amendment C) — untracked going forward but the physical files were archived, not removed from disk.

The only "mishmar" string anywhere in `REORG_EXECUTION_REPORT.md` is this, in §4, about two Windows-locked **napari log files** (not training assets):
> "Two Windows file locks blocked full moves: `microsam_3d/debug.log` and `_napari_mishmar_microSAM_{log,err}.txt` are held open by another process... Copies exist and are tracked at the new locations; the old-path physical files remain orphaned on disk (gitignored so they stop resurfacing). **The maintainer should delete these two old-path files manually** once whatever holds them is closed."

These are explicitly **not yet deleted** (flagged for Rony to delete manually later) and are unrelated to any checkpoint or inference output.

**Conclusion: the reorg did not delete any Mishmar HaNegev training output, checkpoint, or inference output — it couldn't have, since none of that ever lived in the repo it operated on.**

## 2. Checkpoint / results-directory hits found locally

| Path | Size | Date | Note |
|---|---|---|---|
| `C:\Users\rony.schwartz\Documents\nnUNet_resources\mishmar_hanegev\` | 0 bytes (empty folder, 0 files) | 2026-05-09 | Confirmed empty via `Get-ChildItem -Recurse` (0 items) and `dir` — an abandoned/never-populated local mirror attempt, not a usable checkpoint source |
| `C:\Users\rony.schwartz\Documents\nnUNet_resources\bnei_reem\...\checkpoint_best.pth` / `checkpoint_final.pth` (×3 files) | ~236–247 MB each | 2026-04-22 / 2026-05-14 | **Bnei Re'em only** — found by the same sweep, confirms local mirrors exist for Bnei Re'em but were simply never made for Mishmar |
| Mishmar checkpoint anywhere on C:\, D:\, E:\ (outside the inaccessible `Yael_Mishael` tree), P:\ | — | — | **NOT FOUND** (recursive sweep of C:\ complete with zero Mishmar hits; D:\/E:\/P:\ sweep was still running at report time — see note below) |

**Registry-confirmed real checkpoint location** (`01_data_ingestion/registry/data_registry.json`), never local by design:
`\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2\nnUNet_results\Dataset777_GCEF\nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres\fold_0\checkpoint_final.pth`

**Sweep completeness — both sweeps now fully finished, all 4 drives:**
- Directory-name sweep (`nnUNet_resources`/`remote_computer backup`/`multi_sample_mishmar*`/`Yael_Mishael`) found exactly two hits total, both already listed above — the empty local mirror on C:\ and the access-denied `E:\PROJECTS\Yael_Mishael` — nowhere else on C:\, D:\, E:\, or P:\.
- Checkpoint-filename sweep (`checkpoint_final.pth`/`checkpoint_best.pth`) found: 3 Bnei Re'em checkpoints on C:\ (listed above); 6 unrelated third-party checkpoints on D:\ (`D:\ctcdfp\OrsPythonPlugins\...\TotalSegmentator\...` and `...\MRSegmentator\...`, dated 2025-11-21 — a medical-imaging plugin's bundled weights, nothing to do with this project or Mishmar); **zero** hits anywhere on E:\ or P:\.

**No Mishmar HaNegev checkpoint exists anywhere on this machine outside the access-denied `E:\PROJECTS\Yael_Mishael` folder.** Combined with §3's direct evidence that the checkpoint was loaded and used successfully from that exact folder less than an hour before this sweep ran, this rules out deletion: the file is who-knows-exactly-where-but-almost-certainly-still-inside that folder, just currently unreadable by this account.

## 3. Share/folder reachability

**Machine identity matters here:** this session is running directly on the machine named `HIVE3065` (`$env:COMPUTERNAME` = `HIVE3065`, confirmed by `ipconfig`). So `\\hive3065\Yael_Mishael\...` (used throughout the codebase) is a loopback reference to a share on *this same machine*, and `E:\PROJECTS\Yael_Mishael` is that share's actual folder on local disk — no VPN or remote network hop is involved at all.

- **SMB share list** (`Get-SmbShare` / `net share`): `Yael_Mishael` is **absent**. Every one of the ~70 other lab folders under `E:\PROJECTS\` (`alon_nissan_lab`, `anat_kahan_lab`, ... `zvi_yaari_lab`) is published as an identically-named share; `Yael_Mishael` alone is not in that list, despite the folder existing on disk.
- **UNC path** `\\hive3065\Yael_Mishael\...`: `Test-Path` → `False` (not "access denied" — consistent with the share being unpublished, i.e. not currently shared out).
- **Z: drive** (used by `DATA_CATALOG.md`/`PROJECT_STATUS.md` for raw-scan paths): not currently mapped in this session (`Test-Path "Z:\"` → `False`; `Get-PSDrive` shows only C/D/E/P).
- **Local NTFS path** `E:\PROJECTS\Yael_Mishael`: `Test-Path` on the folder itself → **`True`** (it exists). But every attempt to look *inside* it fails with **"Access is denied"**: `Get-ChildItem`, `dir`, `Get-Acl`, `icacls`, and `Test-Path` on three specific, known-to-exist files all return the same error:
  - `...\nnUNet_results\...\fold_0\checkpoint_final.pth` (the Mishmar `i2_loess` checkpoint) → Access is denied
  - `...\mishmar_hanegev_Cu011_samp_2_Rec_nlm\inference_output_concat_loess_i2\mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz` (today's inference output, see below) → Access is denied
  - `...\10.5\mishmar_hanegev_Cu011_samp_2_Rec_nlm.tif` (the raw volume) → Access is denied
- **Account context**: current user is `hive3065\rony.schwartz`, a standard (non-admin) account — `whoami /priv` shows no elevated privileges, and it is not in `BUILTIN\Administrators`. It **is**, however, listed in `whoami /groups` as a member of `HIVE3065\_Yael_Mishael` — a group that looks purpose-built to grant this exact access — yet access is still denied. This points to a misconfigured/incomplete ACL grant or a stale security token (group membership not yet reflected in the current logon session), not a policy that's working as intended.

**Timestamp evidence this broke very recently, not at any past date:** `04_inference/scripts/cu011_loess_i2_inference_log.txt` (untracked, present in the working tree, file mtime **2026-09-21 16:06:59**, less than an hour before this check) shows a complete, error-free nnU-Net inference run — it loaded the `i2_loess` checkpoint from the exact hive path above and finished by writing:
> `DONE - mishmar_hanegev_Cu011_samp_2_Rec_nlm prediction with loess_i2 model: \\hive3065\Yael_Mishael\...\inference_output_concat_loess_i2\mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz (16.3 MB)`

One second later (mtime **16:06:59.48**), a napari-viewer launch script (`06_reporting/scripts/_launch_napari_mishmar_Cu011_15um_loess_i2.py`) was created alongside a companion log that is **0 bytes** — consistent with the script's very first file-existence check (`os.path.isfile(VOL)`, before any `print()` runs) failing immediately. Directly re-testing those same three paths in this session (just now) all return "Access is denied." **So the checkpoint and data were reachable and used successfully earlier this same hour, and access broke somewhere between that successful inference run and the napari attempt that followed it one second later** — this is a live, very-recent access problem, not something the 2026-07/08 reorg (or anything else from weeks/months ago) could have caused.

## 4. Usable pre-existing Mishmar HaNegev inference output (already on disk, not blocked)

| Path | Date | What it shows |
|---|---|---|
| `06_reporting/selected_outputs/mishmar_hanegev2_slice_exports/mishmar_hanegev_Cu011_samp_2_Rec_nlm/slice_{0086,0253,0543}_triplet.png` | 2026-06-02 | Rendered raw/segmentation/overlay slice triplets for the Cu011 sample — directly viewable segmentation figures |
| `06_reporting/selected_outputs/mishmar_hanegev2_slice_exports/nlm_volume/slice_*_triplet.png` + root-level `slice_*_triplet.png` | 2026-05-31 / 06-02 | Same, for `mishmar_native` and an earlier NLM volume |
| `06_reporting/training_diagnostics/curves_mishmar_hanegev.png`, `run_summary_mishmar_hanegev.{csv,png}` | 2026-07-22 | Training-loss/dice curves and run summary for the Mishmar model — usable to show training actually happened and converged |
| `06_reporting/selected_outputs/psd_bulk_density/{figures,psd_table,result}_*mishmar_hanegev*` | — | Pore-size-distribution figures/tables already computed from Mishmar segmentation output |
| `05_evaluation/psd/pom_analysis_20260823_resolution/`, `..._20260824_ablation/`, `..._20260826_final_shape/`, `..._20260829_roi_expansion/`, `..._20260830_interface_metrics/`, `..._20260831_interface_metrics_resmatched/` (all `mishmar_native`/`mishmar_15um`/`mishmar_label_downsample*` subfolders) | 2026-08-23 → 08-31 | Full POM object-level analysis (metrics JSON, cluster CSVs, midslice PNGs, sanity-check JSON) derived from Mishmar segmentation — this is most of the reportable POM/interface-metrics narrative already in `PROJECT_STATUS.md` |
| `05_evaluation/psd/pom_analysis_20260829_roi_expansion/pipeline_work/mishmar_native_5p85um/`, `mishmar_second_8p8um/` | 2026-08-29/30 | ROI-expanded intermediate segmentation volumes |
| `logs_archive/training/mishmar_hnegev_scratch/`, `mishmar_hnegev_trained/` | git-tracked | Short GPU/launch header logs only (32 lines each) — confirm training jobs were launched, but the actual per-epoch nnU-Net training log lived only on the hive share and is not available locally |

All of the above are either already git-tracked or present untracked on disk right now and were unaffected by the access problem in §3 (they were generated in the past and copied into the repo tree before today).

## 5. Cross-check against `DATA_CATALOG.md` / `PROJECT_STATUS.md`

Both documents are internally consistent with what's on disk and don't overclaim: `DATA_CATALOG.md` correctly lists all 5 Mishmar HaNegev physical scans, their storage location (`Z:\Rony\mishmar_hanegev_maoz\...`), and processing status; `PROJECT_STATUS.md` §"Scans note" correctly describes the `i2_loess` model and the `Cu011_samp_2` POM-collapse finding, citing the same checkpoint path confirmed in §2/§3 above. Neither document claims anything is available that isn't — the one discrepancy worth flagging is that both docs point to `Z:\Rony\...` as if it's a normal, currently-mapped drive, when in fact **no drive is mapped to `Z:` in this session at all** (§3) — anyone following those doc paths right now would hit the same access wall found here, and should be pointed at this report rather than assuming the docs are stale.

---

*Full-disk recursive sweep (D:\, E:\, P:\ for `nnUNet_resources`/checkpoint files) was still running in the background when this report was generated; this file will be updated if it surfaces anything beyond the local Bnei Re'em mirrors already found on C:\.*


> **2026-10-04:** Share access restored (read via E:\PROJECTS\Yael_Mishael\...); nothing was deleted. Earlier statements that the share/files were inaccessible are superseded. See  6_reporting/missing_data_20261004/REPORT.md.
