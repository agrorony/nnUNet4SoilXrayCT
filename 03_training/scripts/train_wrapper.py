"""
Wrapper for nnUNet training with PyTorch 2.6 compatibility patches.

On Windows, multiprocessing uses the 'spawn' method: each worker process
re-imports this file as '__mp_main__' (not '__main__'), so the guard
`if __name__ == '__main__':` is False in workers, preventing them from
re-calling run_training_entry().

Patches applied (main process only):
  1. torch.load weights_only=False — nnUNet checkpoints contain numpy objects
     that fail PyTorch 2.6's new safe-load restriction.
  2. load_pretrained_weights — skips shape-mismatched keys; iter02 used all-
     (2,2,2) pool strides, iter03 plans use (1,2,2) for stages 4-5, so
     decoder.transpconvs.[0,1].weight have incompatible shapes.

Usage:
    python _train_wrapper.py <dataset_id> <config> <fold> -tr <trainer> \\
        -pretrained_weights <path>
"""
import sys
import torch

# Patch torch.load at the top level so it is in effect for all code paths
# (including any lazy imports that happen later in this process).
_orig_load = torch.load

def _patched_load(f, *args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _orig_load(f, *args, **kwargs)

torch.load = _patched_load


if __name__ == '__main__':
    # Import nnunetv2 only in the main process.
    # Workers (re-imported as '__mp_main__') do not enter this block,
    # so they skip the heavy imports and the run_training_entry() call.
    import nnunetv2.run.run_training as _rtr_mod
    import nnunetv2.run.load_pretrained_weights as _lpw_mod

    def _patched_load_pretrained(model, fname, verbose=False):
        """Load pretrained weights, silently skipping shape-mismatched keys."""
        saved = torch.load(fname, map_location='cpu')
        pretrained_dict = saved['network_weights']
        model_dict = model.state_dict()

        compatible = {}
        skipped = []
        for k, v in pretrained_dict.items():
            if k in model_dict:
                if model_dict[k].shape == v.shape:
                    compatible[k] = v
                else:
                    skipped.append(
                        f"  shape mismatch  {k}: "
                        f"pretrained={tuple(v.shape)}, "
                        f"network={tuple(model_dict[k].shape)}"
                    )
            else:
                skipped.append(f"  missing key     {k}")

        model.load_state_dict(compatible, strict=False)
        n_loaded, n_total = len(compatible), len(pretrained_dict)
        print(f"[pretrained_weights] Loaded {n_loaded}/{n_total} keys from checkpoint.")
        if skipped:
            n = len(skipped)
            print(f"[pretrained_weights] Skipped {n} incompatible/missing keys:")
            for s in skipped[:30]:
                print(s)
            if n > 30:
                print(f"  ... ({n - 30} more)")

    # Replace the binding that run_training.maybe_load_checkpoint resolves
    # at call time (Python global lookup goes through the module's __dict__).
    _rtr_mod.load_pretrained_weights = _patched_load_pretrained
    _lpw_mod.load_pretrained_weights = _patched_load_pretrained

    from nnunetv2.run.run_training import run_training_entry
    run_training_entry()
