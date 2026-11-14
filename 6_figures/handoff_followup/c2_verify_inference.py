"""Part C1/C2: re-run nnU-Net inference for one UNVERIFIED volume, by the same route as the original run,
into a NEW folder, and write the inference log that was missing.

Route (from the original drivers: 4_inference/run_inference.py (was 04_inference/scripts/run_inference.py), the packaged
_run_inference_fresh_bnei_reem_i4.py and _run_inference_maoz_2_8p8um_loess_i2.py):
  nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False, perform_everything_on_device=False)
  on the existing pre-split chunk folder (inference_input, *_0000.nii.gz), fold 0, checkpoint_final.pth,
  then 4_inference/postprocessing_nnUNet_predict_concatenate.py -i <pred> -o <concat>.
Equivalent CLI: nnUNetv2_predict_from_modelfolder -i <chunks> -o <pred> -m <model> -f 0 -chk checkpoint_final.pth
  --disable_tta -step_size 0.5  (the API is used here so that perform_everything_on_device=False matches the original).

Nothing is written outside <out_root>/<run>/. Inputs and the model are only read.

Usage: python c2_verify_inference.py <run_key> <out_root> <repo_dir>
"""
import datetime
import glob
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys

RES = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
RUNS = {
    'bnei_reem_fresh_bnei_reem_i4': dict(
        model_root='multi_sample_fresh_bnei_reem_i4',
        trainer='nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr',
        chunks=os.path.join(RES, 'bnei_reem_iter04', 'inference_input'),
        full_input=os.path.join(RES, 'bnei_reem_iter04', 'nifti_predict', 'nlm_volume_0000.nii.gz'),
        original_pred=os.path.join(RES, 'bnei_reem_fresh_bnei_reem_i4', 'inference_output'),
        original_concat=os.path.join(RES, 'bnei_reem_fresh_bnei_reem_i4', 'inference_concatenated', 'nlm_volume.nii.gz'),
        out_name='nlm_volume.nii.gz',
        driver='01_volumes/bnei_reem_fresh_bnei_reem_i4/provenance/_run_inference_fresh_bnei_reem_i4.py'),
    'mishmar_hanegev_maoz_3_5p85um': dict(
        model_root='multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2',
        trainer='nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss',
        chunks=os.path.join(RES, 'mishmar_hanegev_maoz_3_5p85um', 'inference_input'),
        full_input=os.path.join(RES, 'mishmar_hanegev_maoz_3_5p85um', 'nifti_predict', 'mishmar_hanegev_maoz_3_5p85um_0000.nii.gz'),
        original_pred=os.path.join(RES, 'mishmar_hanegev_maoz_3_5p85um', 'inference_output_loess_i2'),
        original_concat=os.path.join(RES, 'mishmar_hanegev_maoz_3_5p85um', 'inference_output_concat_loess_i2', 'mishmar_hanegev_maoz_3_5p85um.nii.gz'),
        out_name='mishmar_hanegev_maoz_3_5p85um.nii.gz',
        driver='no driver script found; same settings as run_inference.py / the 8.8 um driver (predict_from_raw_data_args.json: chunk folder inference_input)'),
    'mishmar_hanegev_maoz_2_8p8um': dict(
        model_root='multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2',
        trainer='nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss',
        chunks=os.path.join(RES, 'mishmar_hanegev_maoz_2_8p8um', 'inference_input'),
        full_input=os.path.join(RES, 'mishmar_hanegev_maoz_2_8p8um', 'nifti_predict', 'mishmar_hanegev_maoz_2_8p8um_0000.nii.gz'),
        original_pred=os.path.join(RES, 'mishmar_hanegev_maoz_2_8p8um', 'inference_output_loess_i2'),
        original_concat=os.path.join(RES, 'mishmar_hanegev_maoz_2_8p8um', 'inference_output_concat_loess_i2', 'mishmar_hanegev_maoz_2_8p8um.nii.gz'),
        out_name='mishmar_hanegev_maoz_2_8p8um.nii.gz',
        driver='01_volumes/mishmar_hanegev_maoz_2_8p8um/provenance/_run_inference_maoz_2_8p8um_loess_i2.py'),
}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def mtime(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(sep=' ', timespec='seconds')


def main():
    key, out_root, repo = sys.argv[1:4]
    cfg = RUNS[key]
    out = os.path.join(out_root, key)
    pred_dir = os.path.join(out, 'inference_output')
    concat_dir = os.path.join(out, 'inference_concatenated')
    assert not os.path.exists(pred_dir) and not os.path.exists(concat_dir), f'{out} already has outputs; refusing to overwrite'
    os.makedirs(pred_dir); os.makedirs(concat_dir)
    model_dir = os.path.join(RES, cfg['model_root'], 'nnUNet_results', 'Dataset777_GCEF', f"{cfg['trainer']}__nnUNetPlans__3d_fullres")
    ckpt = os.path.join(model_dir, 'fold_0', 'checkpoint_final.pth')
    concat_script = os.path.join(repo, '4_inference', 'postprocessing_nnUNet_predict_concatenate.py')  # 2026-11 layout (was 04_inference/)
    for k in ('nnUNet_raw', 'nnUNet_preprocessed', 'nnUNet_results'):
        os.environ[k] = os.path.join(RES, cfg['model_root'], k)
    os.environ['nnUNet_compile'] = 'false'

    import torch
    import nnunetv2
    import importlib.metadata as md
    _orig = torch.load

    def _patched(f, *a, **kw):  # PyTorch >= 2.6 checkpoint compatibility, as in the original drivers
        kw.setdefault('weights_only', False)
        return _orig(f, *a, **kw)
    torch.load = _patched
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    chunks = sorted(glob.glob(os.path.join(cfg['chunks'], '*_0000.nii.gz')))
    log = dict(run=key, host=socket.gethostname(), python=sys.executable, platform=platform.platform(),
               command_line=' '.join([sys.executable] + sys.argv),
               route='nnUNetPredictor API on pre-split chunks + postprocessing_nnUNet_predict_concatenate.py (same as original driver)',
               original_driver=cfg['driver'],
               equivalent_cli=f'nnUNetv2_predict_from_modelfolder -i "{cfg["chunks"]}" -o "{pred_dir}" -m "{model_dir}" -f 0 -chk checkpoint_final.pth --disable_tta -step_size 0.5',
               predictor_settings=dict(tile_step_size=0.5, use_gaussian=True, use_mirroring=False, perform_everything_on_device=False,
                                       use_folds=[0], checkpoint_name='checkpoint_final.pth', num_processes_preprocessing=1,
                                       num_processes_segmentation_export=1),
               nnunetv2_version=md.version('nnunetv2'), torch_version=torch.__version__, cuda=torch.version.cuda,
               gpu=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
               CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
               trainer_file=dict(path=os.path.join(os.path.dirname(nnunetv2.__file__), 'training', 'nnUNetTrainer', 'variants', 'sampling', 'nnUNetTrainer_betterIgnoreSampling.py')),
               model_dir=model_dir,
               checkpoint=dict(path=ckpt, sha256=sha(ckpt), mtime=mtime(ckpt), size=os.path.getsize(ckpt)),
               plans_json_sha256=sha(os.path.join(model_dir, 'plans.json')),
               input_chunk_dir=cfg['chunks'],
               input_chunks=[dict(file=os.path.basename(c), sha256=sha(c), mtime=mtime(c)) for c in chunks],
               full_input_volume=dict(path=cfg['full_input'], sha256=sha(cfg['full_input']), mtime=mtime(cfg['full_input'])),
               concatenate_script=dict(path=concat_script, sha256=sha(concat_script)),
               original_prediction=dict(path=cfg['original_concat'], sha256=sha(cfg['original_concat']), mtime=mtime(cfg['original_concat'])),
               output_pred_dir=pred_dir, output_concat_dir=concat_dir)
    log['trainer_file']['sha256'] = sha(log['trainer_file']['path'])
    log['start'] = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    print(json.dumps({k: v for k, v in log.items() if k != 'input_chunks'}, indent=1), flush=True)

    predictor = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False, perform_everything_on_device=False,
                                device=torch.device('cuda'), verbose=False, allow_tqdm=True)
    predictor.initialize_from_trained_model_folder(model_dir, use_folds=(0,), checkpoint_name='checkpoint_final.pth')
    predictor.predict_from_files(cfg['chunks'], pred_dir, save_probabilities=False, overwrite=False,
                                 num_processes_preprocessing=1, num_processes_segmentation_export=1,
                                 folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0)
    log['inference_end'] = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    res = subprocess.run([sys.executable, concat_script, '-i', pred_dir, '-o', concat_dir], capture_output=True, text=True)
    log['concatenate_stdout'] = res.stdout[-4000:]
    log['concatenate_returncode'] = res.returncode
    if res.returncode != 0:
        log['concatenate_stderr'] = res.stderr[-4000:]
    out_file = os.path.join(concat_dir, cfg['out_name'])
    log['end'] = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    if os.path.isfile(out_file):
        log['output'] = dict(path=out_file, sha256=sha(out_file), size=os.path.getsize(out_file))
    log['per_chunk_predictions'] = [dict(file=os.path.basename(p), sha256=sha(p)) for p in sorted(glob.glob(os.path.join(pred_dir, '*.nii.gz')))]
    with open(os.path.join(out, 'inference_log.json'), 'w') as f:
        json.dump(log, f, indent=1)
    with open(os.path.join(out, 'inference_log.txt'), 'w', encoding='utf-8') as f:
        for k in ('run', 'command_line', 'route', 'original_driver', 'equivalent_cli', 'start', 'inference_end', 'end', 'host', 'gpu',
                  'CUDA_VISIBLE_DEVICES', 'nnunetv2_version', 'torch_version', 'cuda', 'model_dir', 'checkpoint', 'plans_json_sha256',
                  'trainer_file', 'predictor_settings', 'input_chunk_dir', 'full_input_volume', 'concatenate_script',
                  'original_prediction', 'output', 'concatenate_returncode'):
            f.write(f'{k}: {log.get(k)}\n')
        f.write('input_chunks:\n')
        for c in log['input_chunks']:
            f.write(f"  {c['file']}  sha256 {c['sha256']}  mtime {c['mtime']}\n")
    print('DONE', key, log.get('output'), 'concat rc', res.returncode)
    if res.returncode != 0:
        print(res.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
