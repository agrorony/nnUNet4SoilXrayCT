"""Part D (read-only), follow-up to D1/D2: are the two Bnei Re'em raw scan folders distinct acquisitions?

For each raw folder: non-projection files (name, bytes, mtime), projection count and min/max mtime, and verbatim
date/size lines from every *.log. Then sha256 of projections 0, 450, 900, 1350, 1799 in both folders, to test
whether one folder holds a copy of the other's projections.

Usage: python d2b_raw_projection_check.py <out_json> <raw_folder_A> <raw_folder_B>
"""
import datetime
import hashlib
import json
import os
import re
import sys

PROJ = re.compile(r'^(?P<prefix>.+?)(?P<idx>\d{8})\.tif$', re.I)
KEYS = re.compile(r'^(Study Date and Time|Scan duration|Image Pixel Size \(um\)|Filename Prefix|Data Directory|Number of Files|'
                  r'Rotation Step|Exposure|Source Voltage|Filter|Object to Source|Camera to Source|Number of Rows|Number of Columns|'
                  r'Scanner|Software Version)', re.I)


def ts(t):
    return datetime.datetime.fromtimestamp(t).isoformat(sep=' ', timespec='seconds')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def scan(folder):
    files = os.listdir(folder)
    proj, other = {}, []
    for f in files:
        p = os.path.join(folder, f)
        if os.path.isdir(p):
            other.append(dict(name=f + '/', mtime=ts(os.path.getmtime(p))))
            continue
        m = PROJ.match(f)
        if m and '_rec' not in f.lower() and '_prev' not in f.lower():
            proj[int(m['idx'])] = f
        else:
            other.append(dict(name=f, bytes=os.path.getsize(p), mtime=ts(os.path.getmtime(p))))
    mt = [os.path.getmtime(os.path.join(folder, f)) for f in proj.values()]
    logs = {}
    for o in other:
        if o['name'].lower().endswith('.log'):
            with open(os.path.join(folder, o['name']), encoding='latin-1') as fh:
                logs[o['name']] = [ln.rstrip('\r\n') for ln in fh if KEYS.match(ln.strip())]
    return dict(folder=folder, n_projections=len(proj), proj_index_range=[min(proj), max(proj)] if proj else None,
                proj_mtime_min=ts(min(mt)) if mt else None, proj_mtime_max=ts(max(mt)) if mt else None,
                example_names=[proj[min(proj)], proj[max(proj)]] if proj else None,
                other_files=sorted(other, key=lambda o: o['mtime']), log_lines=logs, _proj=proj)


def main():
    out, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
    A, B = scan(a), scan(b)
    cmp = []
    for i in (0, 450, 900, 1350, 1799):
        fa, fb = A['_proj'].get(i), B['_proj'].get(i)
        if fa and fb:
            ha, hb = sha(os.path.join(a, fa)), sha(os.path.join(b, fb))
            cmp.append(dict(index=i, a=fa, b=fb, sha_a=ha, sha_b=hb, identical=ha == hb,
                            mtime_a=ts(os.path.getmtime(os.path.join(a, fa))), mtime_b=ts(os.path.getmtime(os.path.join(b, fb)))))
    for d in (A, B):
        d.pop('_proj')
    res = dict(A=A, B=B, projection_comparison=cmp)
    json.dump(res, open(out, 'w'), indent=1)
    for d in (A, B):
        print('==', d['folder'])
        print(f"  projections: {d['n_projections']} idx {d['proj_index_range']} mtime {d['proj_mtime_min']} .. {d['proj_mtime_max']}  e.g. {d['example_names']}")
        for o in d['other_files']:
            print('   ', o)
        for k, v in d['log_lines'].items():
            print('  log', k)
            for ln in v:
                print('     ', ln)
    for c in cmp:
        print('proj', c['index'], 'identical' if c['identical'] else 'DIFFERENT', c['mtime_a'], c['mtime_b'])


if __name__ == '__main__':
    main()
