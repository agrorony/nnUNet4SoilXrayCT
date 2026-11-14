"""Part B4 (file swap, approved files only): move each pre-flip original to the backup folder
(same relative path), then rename <name>_aligned.<ext> to the original filename. sha256 checked before/after.

Usage: python b4_swap.py <B2_B3_results.json> <package_dir> <backup_dir> <out_log.json>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def main():
    res, pkg, bak, out = sys.argv[1:5]
    pkg, bak = Path(pkg), Path(bak)
    log = []
    for r in json.load(open(res)):
        if not r['aligned_path']:
            continue
        orig = pkg / r['seg']
        al = Path(r['aligned_path'])
        dst = bak / r['seg']
        assert orig.exists() and al.exists() and not dst.exists(), r['seg']
        h_orig, h_al = sha(orig), sha(al)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(orig), str(dst))
        assert sha(dst) == h_orig
        al.rename(orig)
        assert sha(orig) == h_al
        log.append(dict(file=r['seg'], transform=r['transform'], original_sha256=h_orig, backup=str(dst),
                        new_sha256=h_al, label_counts=r['label_counts']))
        print('swapped', r['seg'])
    json.dump(log, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
