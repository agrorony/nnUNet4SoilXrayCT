"""Package v3, step 1: copy the files a reader needs from the v2 staging folder (and a few from the repo) into the
v3 layout, and write PACKAGE_MAP_v2_to_v3.csv next to the future ZIP.

Copy only: the v2 staging folder and the repo are read, never written. Every copy is sha256-checked.
READMEs are not copied here (v3_readmes.py writes them); the v2 READMEs are mapped to their v3 rewrites in the map.

Usage: python v3_copy.py <v2_package_dir> <repo_dir> <v3_package_dir> <map_csv> <log_json>
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCANS = {
    'bnei_reem_specA_unified': '01_scans/vertisol_A',
    'bnei_reem_specB_unified': '01_scans/vertisol_B',
    'bnei_reem_fresh_bnei_reem_i4': '01_scans/vertisol_B/april_processing',
    'mishmar_hanegev_maoz_3_5p85um': '01_scans/loess_5p85um_maoz',
    'mishmar_hanegev_maoz_2_8p8um': '01_scans/loess_8p8um_maoz',
    'Cu011_samp_2': '01_scans/loess_samp2',
    'Rehovot_samp2_highkV_Cu0.11_15um': '01_scans/sand_samp2',
    'Rehovot_samp3_highkV_Cu0.11_15um': '01_scans/sand_samp3',
}
FILE_RENAMES = {'segmentation_nnunet_bnei_reem_i4.nii.gz': 'segmentation_nnunet_reference_bnei_reem_i4.nii.gz',
                'segmentation_nnunet_loess_i2.nii.gz': 'segmentation_nnunet_reference_loess_i2.nii.gz'}
MODELS = {'bnei_reem_i4': ('03_models/vertisol_i4', 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres',
                           'fresh_bnei_reem_i4.yaml', 'training_log_2026_7_5_16_52_21.txt'),
          'mishmar_loess_i2': ('03_models/loess_i2', 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres',
                               'mishmar_hanegev_maoz_3_5p85um_loess_i2.yaml', 'training_log_2026_7_15_13_43_55.txt')}
AO = '05_analysis_outputs'
TE = f'{AO}/connectivity/Topology_Metrics_Aug2026'
CF = f'{TE}/connectivity_function'
TRACK_E = ['psd_diag_20260907T103058_bnei_reem_specA_unified', 'psd_diag_20260907T122221_bnei_reem_specB_unified',
           'psd_diag_20260902T160041_mishmar_native_label_downsample_15um', 'psd_diag_20260902T215639_mishmar_second_8p8um_label_downsample_15um',
           'psd_diag_20260824T135838_mishmar_15um_cu011samp2', 'psd_diag_20260824T135738_rehovot_samp_2_full_volume',
           'psd_diag_20260829T164636_rehovot_samp3_full_volume']
CHI_R = ['chi_r_bnei_reem_specA_unified', 'chi_r_bnei_reem_specB_unified', 'chi_r_mishmar_native_label_downsample_15um',
         'chi_r_mishmar_second_8p8um_label_downsample_15um', 'chi_r_mishmar_15um', 'chi_r_rehovot', 'chi_r_rehovot_samp3']
DIST = {f'{TE}/raw/psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4/summary_distance_metrics.json':
        '05_results/distances/psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4/summary_distance_metrics.json',
        f'{TE}/raw/psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2/summary_distance_metrics.json':
        '05_results/distances/psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2/summary_distance_metrics.json',
        f'{AO}/distances/rehovot_distance_metrics_20260815/summary_distance_metrics.json':
        '05_results/distances/rehovot_distance_metrics_20260815/summary_distance_metrics.json'}
REPO = 'REPO:'   # source prefix for files taken from the repo (main)

# categories for v2 files that are not in v3 (first matching prefix wins)
LEFT_OUT = [
    ('03_models/', 'models: checkpoint_best.pth and nnU-Net extras (debug.json, dataset_fingerprint.json, analytics/, validation/)'),
    (f'{AO}/pom/pom_analysis_20260830_interface_metrics/', 'POM interface: earlier 2026-08-30 run (superseded by the resolution-matched 2026-08-31 run)'),
    (f'{AO}/pom/pom_analysis_20260831_interface_metrics_resmatched/', 'POM interface: per-soil summaries, scripts, figure, README of the reported run'),
    (f'{AO}/pom/', 'POM clustering runs (dropped Aug 2026) and their exploratory outputs'),
    (f'{TE}/raw/', 'Track E: logs, diagnostics.json, psd_raw_data.csv/psd_table.csv, block files, PNGs, unreported runs'),
    (f'{TE}/connectivity_function/', 'connectivity: chi(r) files not behind a reported r* (older/recheck runs, native resolution) and the chi(r) plot'),
    (f'{TE}/bnei_reem_specB_visual_evidence/', 'connectivity: 2026-08 specimen-B visual evidence and notes (superseded by the follow-up Part D)'),
    (f'{TE}/', 'connectivity: run-summary notes (Markdown)'),
    (f'{AO}/connectivity/missing_data_20261004/training_curves/', 'training curves (duplicates; nnU-Net curves are in 03_models)'),
    (f'{AO}/connectivity/missing_data_20261004/', 'connectivity: 2026-10-04 missing-data report, figure copy and duplicate Track E files'),
    (f'{AO}/psd/', 'pore size: per-subvolume PSD runs, logs, scripts, checkpoints, figures, intermediate files'),
    (f'{AO}/distances/', 'distances: comparison file, figure and notes'),
    (f'{AO}/tortuosity/', 'tortuosity: scripts, solver logs, work/ intermediates, figure'),
    (f'{AO}/README.md', 'v2 analysis-outputs README (replaced by 05_results/README.md)'),
    ('06_figures/synopsis_outputs/', 'figures: synopsis_outputs'),
    ('06_figures/selected_outputs/', 'figures: selected_outputs'),
    ('06_figures/training_diagnostics/', 'figures: training_diagnostics (nnU-Net curves are in 03_models)'),
    ('06_figures/render3d_', 'figures: render scripts, logs, parameters and contact sheets (in the repo)'),
    ('06_figures/figure7_20261004/', 'figures: segmentation-example script, SVG and slice info (in the repo)'),
    ('06_figures/', 'figures: v2 figures README'),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def plan(v2, repo):
    P = {}  # v3_rel -> source (v2 rel, or REPO:rel)
    for d in sorted((v2 / '01_volumes').iterdir()):
        for f in sorted(d.rglob('*')):
            if f.is_file() and f.name != 'README.md':
                rel = f.relative_to(d).as_posix()
                parts = rel.split('/')
                parts[-1] = FILE_RENAMES.get(parts[-1], parts[-1])
                P[f"{SCANS[d.name]}/{'/'.join(parts)}"] = f.relative_to(v2).as_posix()
    for f in sorted((v2 / '02_annotations').rglob('*')):
        if f.is_file() and f.name != 'README.md':
            P[f.relative_to(v2).as_posix()] = f.relative_to(v2).as_posix()
    for old, (new, tr, yaml, log) in MODELS.items():
        b = f'03_models/{old}'
        P[f'{new}/splits_final.json'] = f'{b}/splits_final.json'
        for x in ('plans.json', 'dataset.json', 'fold_0/checkpoint_final.pth', 'fold_0/progress.png', f'fold_0/{log}'):
            P[f'{new}/{tr}/{x}'] = f'{b}/{tr}/{x}'
        P[f'{new}/{yaml}'] = f'03_models/run_configs/{yaml}'
    P['03_models/nnUNetTrainer_betterIgnoreSampling.py'] = '03_models/nnUNetTrainer_betterIgnoreSampling.py'
    for f in sorted((v2 / '04_code').rglob('*')):
        if f.is_file() and f.relative_to(v2).as_posix() != '04_code/README.md':
            P[f.relative_to(v2).as_posix()] = f.relative_to(v2).as_posix()
    for f in sorted((v2 / '07_lab_data_and_writeup').rglob('*')):
        if f.is_file() and f.relative_to(v2).as_posix() != '07_lab_data_and_writeup/README.md':
            P['07_lab_data/' + f.relative_to(v2 / '07_lab_data_and_writeup').as_posix()] = f.relative_to(v2).as_posix()
    # 05_results
    R = '05_results'
    psd_a2, fig4 = f'{AO}/psd/psd_A2_reanalysis_20260822', f'{AO}/psd/fig4_inference_20260815'
    P.update({f'{R}/pore_size_classes/class_metrics.csv': f'{psd_a2}/class_metrics.csv',
              f'{R}/pore_size_classes/class_stats_results.json': f'{psd_a2}/class_stats_results.json',
              f'{R}/pore_size_classes/A2_summary.md': REPO + '5_analysis/pore_size_distribution/A2_summary.md',
              f'{R}/pore_size_classes/downsample_comparison.json': f'{psd_a2}/downsample_comparison.json',
              f'{R}/pore_size_classes/fig4_subvolumes/stats_results.json': f'{fig4}/stats_results.json',
              f'{R}/pore_size_classes/fig4_subvolumes/subvolume_metrics.csv': f'{fig4}/subvolume_metrics.csv',
              f'{R}/pore_size_classes/fig4_subvolumes/stats_summary.md': f'{fig4}/stats_summary.md'})
    for r in TRACK_E:
        for x in ('summary.json', 'config.json'):
            P[f'{R}/connectivity/track_e/{r}/{x}'] = f'{TE}/raw/{r}/{x}'
    for c in CHI_R:
        P[f'{R}/connectivity/chi_r/{c}.csv'] = f'{CF}/{c}.csv'
        if (v2 / f'{CF}/{c}.meta.json').is_file():
            P[f'{R}/connectivity/chi_r/{c}.meta.json'] = f'{CF}/{c}.meta.json'
    P[f'{R}/connectivity/rehovot_track_e_samp2_samp3_mean_se.csv'] = f'{AO}/connectivity/missing_data_20261004/rehovot_samp3_track_e/rehovot_track_e_samp2_samp3_mean_se.csv'
    P[f'{R}/connectivity/figures_data_export.md'] = REPO + '5_analysis/connectivity/figures_data_export.md'
    P[f'{R}/connectivity/porosity_normalization_results.txt'] = REPO + '5_analysis/porosity_normalization/results.txt'
    for s, d in DIST.items():
        P[d] = s
    tort = f'{AO}/tortuosity/tortuosity_subvolumes_20261004'
    for x in ('tortuosity_subvolumes.csv', 'tortuosity_summary.csv', 'convergence_summary.csv', 'stats.json'):
        P[f'{R}/tortuosity/{x}'] = f'{tort}/{x}'
    P[f'{R}/tortuosity/REPORT.md'] = REPO + '5_analysis/tortuosity/REPORT.md'
    rm, ab = f'{AO}/pom/pom_analysis_20260831_interface_metrics_resmatched', f'{AO}/pom/pom_analysis_20260824_ablation'
    P.update({f'{R}/pom/all_soils_interface_summary.json': f'{rm}/all_soils_interface_summary.json',
              f'{R}/pom/comparison_table_raw.json': f'{rm}/comparison_table_raw.json',
              f'{R}/pom/pom_spatial_pattern_summary_2soil_clean.json': f'{ab}/pom_spatial_pattern_summary_2soil_clean.json',
              f'{R}/pom/pom_object_features_2soil_clean.csv': f'{ab}/pom_object_features_2soil_clean.csv'})
    # 06_figures
    for f in sorted((repo / '6_figures/write_up_figures').iterdir()):
        if f.suffix in ('.png', '.svg'):
            P[f'06_figures/write_up/{f.name}'] = REPO + f'6_figures/write_up_figures/{f.name}'
    P['06_figures/segmentation_examples/figure7_prediction_panels.png'] = '06_figures/figure7_20261004/figure7_prediction_panels.png'
    for src, dst in (('render3d_bnei_reem_20261013/renders', 'vertisol_B_april_processing'),
                     ('render3d_mishmar_5p85_20261012/renders', 'loess_5p85um_maoz'), ('render3d_pairs_20261013', 'pairs')):
        for f in sorted((v2 / '06_figures' / src).glob('*.png')):
            P[f'06_figures/renders_3d/{dst}/{f.name}'] = f'06_figures/{src}/{f.name}'
    return P


def main():
    v2, repo, v3, map_csv, log_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    assert not v3.exists(), f'{v3} exists'
    P = plan(v2, repo)
    v2_manifest = {r['relative_path']: r for r in csv.DictReader(open(v2 / 'MANIFEST.csv', encoding='utf-8'))}
    copied = {}
    for dst, src in P.items():
        s = repo / src[len(REPO):] if src.startswith(REPO) else v2 / src
        assert s.is_file(), s
        if not src.startswith(REPO):
            assert src in v2_manifest, src
        d = v3 / dst
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        h = sha(d)
        exp = v2_manifest[src]['sha256'] if not src.startswith(REPO) else sha(s)
        assert h == exp, (dst, src)
        copied[dst] = dict(source=src, sha256=h, bytes=d.stat().st_size)
    print(f'copied {len(copied)} files', flush=True)

    # map every v2 file
    by_src = {}
    for dst, c in copied.items():
        by_src.setdefault(c['source'], []).append(dst)
    by_hash = {}
    for dst, c in copied.items():
        by_hash.setdefault(c['sha256'], dst)
    readme_map = {f'01_volumes/{o}/README.md': f'{n}/README.md' for o, n in SCANS.items()}
    readme_map.update({'03_models/bnei_reem_i4/README.md': '03_models/vertisol_i4/README.md',
                       '03_models/mishmar_loess_i2/README.md': '03_models/loess_i2/README.md',
                       '02_annotations/bnei_reem_i4/README.md': '02_annotations/bnei_reem_i4/README.md',
                       '02_annotations/mishmar_loess_i2/README.md': '02_annotations/mishmar_loess_i2/README.md',
                       '04_code/README.md': '04_code/README.md', '07_lab_data_and_writeup/README.md': '07_lab_data/README.md',
                       'README.md': 'README.md'})
    rows, left = [], {}
    for rel, r in sorted(v2_manifest.items()):
        if rel in by_src:
            rows.append((rel, ';'.join(by_src[rel]), 'copied'))
        elif rel in readme_map:
            rows.append((rel, readme_map[rel], 'README rewritten for v3'))
        elif r['sha256'] in by_hash:
            rows.append((rel, by_hash[r['sha256']], 'not copied: same content as this v3 file'))
        else:
            cat = next((c for p, c in LEFT_OUT if rel.startswith(p)), None)
            assert cat, f'no category for {rel}'
            rows.append((rel, 'not in v3', cat))
            left.setdefault(cat, [0, 0])
            left[cat][0] += 1
            left[cat][1] += int(r['bytes'])
    rows.append(('MANIFEST.csv', 'MANIFEST.csv', 'regenerated for v3'))
    with open(map_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['v2_path', 'v3_path', 'note'])
        w.writerows(rows)
    json.dump(dict(copied=copied, left_out=left, n_v2=len(v2_manifest)), open(log_json, 'w'), indent=1)
    print(f'map: {len(rows)} rows; left out by category:')
    for c, (n, b) in sorted(left.items(), key=lambda kv: -kv[1][0]):
        print(f'  {n:4d} files {b / 1e6:9.1f} MB  {c}')


if __name__ == '__main__':
    main()
