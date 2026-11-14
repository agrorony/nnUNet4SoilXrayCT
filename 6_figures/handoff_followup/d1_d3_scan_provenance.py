"""Part D1-D3 (read-only): which Bnei Re'em scan is the canonical volume?

D1/D2: for every reconstruction folder under the given roots (a folder holding *_rec.log or *_rec########.tif):
       number of slices, min/max slice mtime, and verbatim lines from each *_rec.log:
       Data Directory, Filename Prefix, Image Pixel Size (um), Study Date and Time, and every date/time line
       of the [Reconstruction] section.
D3:    files older than a cutoff in the given folders (recursive), with size, mtime and, for images, shape/dtype.

Nothing is written except <out_json>.
Usage: python d1_d3_scan_provenance.py <out_json> --rec <root>... --old <dir>... [--cutoff 2026-04-20]
"""
import argparse
import datetime
import json
import os
import re

SLICE = re.compile(r'_rec\d{8}\.(tif|tiff|bmp|png)$', re.I)
KEYS = ('Data Directory', 'Filename Prefix', 'Image Pixel Size (um)', 'Study Date and Time')


def ts(t):
    return datetime.datetime.fromtimestamp(t).isoformat(sep=' ', timespec='seconds')


def read_log(p):
    out, section = [], None
    with open(p, encoding='latin-1') as f:
        for line in f:
            s = line.rstrip('\r\n')
            if s.startswith('[') and s.endswith(']'):
                section = s
                continue
            key = s.split('=', 1)[0].strip()
            if key in KEYS or (section == '[Reconstruction]' and re.search(r'date|time', key, re.I)):
                out.append(dict(section=section, line=s))
    return out


def scan_rec(root):
    res = []
    for d, _, files in os.walk(root):
        slices = [f for f in files if SLICE.search(f)]
        logs = [f for f in files if f.lower().endswith('_rec.log')]
        if not slices and not logs:
            continue
        r = dict(folder=d, n_slices=len(slices))
        if slices:
            m = [os.path.getmtime(os.path.join(d, f)) for f in slices]
            r.update(slice_mtime_min=ts(min(m)), slice_mtime_max=ts(max(m)), first_slice=min(slices), last_slice=max(slices))
        r['logs'] = [dict(file=f, mtime=ts(os.path.getmtime(os.path.join(d, f))), lines=read_log(os.path.join(d, f))) for f in sorted(logs)]
        res.append(r)
    return res


def scan_old(root, cutoff):
    res = []
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            t = os.path.getmtime(p)
            if t < cutoff:
                e = dict(path=p, bytes=os.path.getsize(p), mtime=ts(t))
                low = f.lower()
                try:
                    if low.endswith(('.tif', '.tiff')):
                        import tifffile
                        with tifffile.TiffFile(p) as tf:
                            s = tf.series[0]
                            e.update(shape=list(s.shape), dtype=str(s.dtype))
                    elif low.endswith('.npy'):
                        import numpy as np
                        a = np.load(p, mmap_mode='r')
                        e.update(shape=list(a.shape), dtype=str(a.dtype))
                    elif low.endswith(('.nii', '.nii.gz')):
                        import nibabel as nib
                        h = nib.load(p).header
                        e.update(shape=list(h.get_data_shape()), dtype=str(h.get_data_dtype()))
                except Exception as ex:  # report, do not fail
                    e['read_error'] = repr(ex)
                res.append(e)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--rec', nargs='+', default=[])
    ap.add_argument('--old', nargs='+', default=[])
    ap.add_argument('--cutoff', default='2026-04-20')
    a = ap.parse_args()
    cutoff = datetime.datetime.fromisoformat(a.cutoff).timestamp()
    out = dict(cutoff=a.cutoff, reconstructions={r: (scan_rec(r) if os.path.isdir(r) else 'NOT FOUND') for r in a.rec},
               older_than_cutoff={r: (scan_old(r, cutoff) if os.path.isdir(r) else 'NOT FOUND') for r in a.old})
    json.dump(out, open(a.out, 'w'), indent=1)
    for root, recs in out['reconstructions'].items():
        print('##', root)
        if isinstance(recs, str):
            print('  ', recs)
            continue
        for r in recs:
            print(f"  {r['folder']}: {r['n_slices']} slices, mtime {r.get('slice_mtime_min')} .. {r.get('slice_mtime_max')}")
            for lg in r['logs']:
                print(f"    {lg['file']} (mtime {lg['mtime']})")
                for ln in lg['lines']:
                    print(f"      {ln['section']} {ln['line']}")
    for root, fl in out['older_than_cutoff'].items():
        print('## older than', a.cutoff, 'in', root, ':', fl if isinstance(fl, str) else len(fl))
        if not isinstance(fl, str):
            for e in fl:
                print('  ', e)


if __name__ == '__main__':
    main()
