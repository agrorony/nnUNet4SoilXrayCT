"""Part A3: content-level duplicate check.

Images: Pearson r on z-scored arrays (stride 2) for every same-shape pair (identity orientation).
Segmentations: pore Dice (stride 2) for every same-shape pair.
Pairs of different shape -> "n/c" in the strict matrices.

Supplementary (catches duplicates stored flipped/transposed or with a 1-2 voxel crop difference):
for every pair whose shapes match up to an axis permutation and differ by <= MAXOFF voxels per axis,
search all 48 signed axis permutations x crop offsets on stride-4 views and report the best |r| / Dice.

Pore label per file: nnU-Net predictions / labelsTr / validation = 5; annotation-space files
(original_annotations, registry_merged_GT) = 6 (rule 7: annotation = nnU-Net + 1); bool Otsu masks = True.

Usage: python a3_content_matrices.py <A2_array_level.json> <out_dir>
"""
import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

MAXOFF = 4


def kind(rel):
    r = rel.lower()
    return 'image' if ('image_preprocessed' in r or '/imagestr/' in r) else 'seg'


def pore_label(rel, dtype):
    if dtype == 'bool':
        return 1
    if 'original_annotations' in rel or 'registry_merged_GT' in rel:
        return 6
    return 5


def short(rel):
    p = rel.split('/')
    if p[0] == '01_volumes':
        return p[1] + '/' + p[-1].replace('.nii.gz', '').replace('image_preprocessed', 'img')
    if p[0] == '02_annotations':
        return p[1] + '/' + ('labelsTr' if 'labelsTr' in rel else 'imagesTr' if 'imagesTr' in rel else '') + '/' + p[-1].replace('.nii.gz', '')
    if p[0] == '03_models':
        return p[1] + '/validation/' + p[-1].replace('.nii.gz', '')
    return rel


def signed_perms():
    for perm in itertools.permutations(range(3)):
        for flips in itertools.product([False, True], repeat=3):
            yield perm, flips


def apply_t(a, perm, flips):
    a = np.transpose(a, perm)
    sl = tuple(slice(None, None, -1) if f else slice(None) for f in flips)
    return a[sl]


def prep(entry, stride):
    a = np.load(entry['cache'], mmap_mode='r')
    if entry['kind'] == 'image':
        return a
    return a  # masks built later, after crop


def score(x, y, k, lab_x, lab_y):
    if k == 'image':
        x = x.astype(np.float64).ravel(); y = y.astype(np.float64).ravel()
        x -= x.mean(); y -= y.mean()
        return float((x @ y) / np.sqrt((x @ x) * (y @ y)))
    mx = (x == lab_x); my = (y == lab_y)
    s = int(mx.sum()) + int(my.sum())
    return float(2 * np.logical_and(mx, my).sum() / s) if s else float('nan')


def strict_pair(args):
    ea, eb = args
    a = np.load(ea['cache'], mmap_mode='r')[::2, ::2, ::2]
    b = np.load(eb['cache'], mmap_mode='r')[::2, ::2, ::2]
    return ea['rel'], eb['rel'], score(np.asarray(a), np.asarray(b), ea['kind'], ea['pore'], eb['pore'])


def search_pair(args):
    ea, eb = args
    A = np.load(ea['cache'], mmap_mode='r')
    B = np.load(eb['cache'], mmap_mode='r')
    best = None
    ident = None
    for perm, flips in signed_perms():
        Bt = apply_t(B, perm, flips)
        if any(abs(sa - sb) > MAXOFF for sa, sb in zip(A.shape, Bt.shape)):
            continue
        common = tuple(min(sa, sb) for sa, sb in zip(A.shape, Bt.shape))
        offs_a = [range(sa - c + 1) for sa, c in zip(A.shape, common)]
        offs_b = [range(sb - c + 1) for sb, c in zip(Bt.shape, common)]
        for oa in itertools.product(*offs_a):
            Ac = A[oa[0]:oa[0] + common[0], oa[1]:oa[1] + common[1], oa[2]:oa[2] + common[2]][::4, ::4, ::4]
            Ac = np.asarray(Ac)
            for ob in itertools.product(*offs_b):
                Bc = np.asarray(Bt[ob[0]:ob[0] + common[0], ob[1]:ob[1] + common[1], ob[2]:ob[2] + common[2]][::4, ::4, ::4])
                s = score(Ac, Bc, ea['kind'], ea['pore'], eb['pore'])
                key = abs(s) if ea['kind'] == 'image' else s
                rec = dict(score=s, perm=list(perm), flips=list(flips), off_a=list(oa), off_b=list(ob))
                if perm == (0, 1, 2) and not any(flips) and ident is None:
                    ident = rec
                if best is None or (not np.isnan(key) and key > (abs(best['score']) if ea['kind'] == 'image' else best['score'])):
                    best = rec
    return ea['rel'], eb['rel'], best, ident


def compatible(sa, sb):
    for perm in itertools.permutations(range(3)):
        if all(abs(sa[i] - sb[p]) <= MAXOFF for i, p in enumerate(perm)):
            return True
    return False


def main():
    a2, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    ents = json.load(open(a2))
    for e in ents:
        e['kind'] = kind(e['rel'])
        e['pore'] = pore_label(e['rel'], e['dtype'])
    out = {}
    with ProcessPoolExecutor(max_workers=30) as ex:
        for k in ('image', 'seg'):
            E = [e for e in ents if e['kind'] == k]
            pairs = [(x, y) for x, y in itertools.combinations(E, 2) if x['shape'] == y['shape']]
            strict = {(a, b): s for a, b, s in ex.map(strict_pair, pairs)}
            cpairs = [(x, y) for x, y in itertools.combinations(E, 2) if compatible(x['shape'], y['shape'])]
            searched = {(a, b): (best, ident) for a, b, best, ident in ex.map(search_pair, cpairs)}
            names = [e['rel'] for e in E]
            # strict matrix
            lines = ['| | ' + ' | '.join(f'{i}' for i in range(len(E))) + ' |', '|' + '---|' * (len(E) + 1)]
            for i, a in enumerate(names):
                row = []
                for j, b in enumerate(names):
                    if i == j:
                        row.append('—'); continue
                    key = (a, b) if (a, b) in strict else (b, a)
                    row.append(f'{strict[key]:.4f}' if key in strict else 'n/c')
                lines.append(f'| {i} | ' + ' | '.join(row) + ' |')
            legend = [f'{i}: `{short(n)}` {tuple(E[i]["shape"])}' + (f' pore={E[i]["pore"]}' if k == 'seg' else '') for i, n in enumerate(names)]
            out[k] = dict(
                legend=legend, matrix_md=lines,
                strict=[dict(a=a, b=b, score=s) for (a, b), s in strict.items()],
                searched=[dict(a=a, b=b, best=bv, identity=iv) for (a, b), (bv, iv) in searched.items()])
    json.dump(out, open(outdir / 'A3_content_level.json', 'w'), indent=1)
    md = []
    for k, lab in (('image', 'Pearson r (z-scored, stride 2, identity orientation)'), ('seg', 'pore Dice (stride 2, identity orientation)')):
        md += [f'## A3 {k}s: {lab}', ''] + out[k]['legend'] + [''] + out[k]['matrix_md'] + ['']
        md += [f'### A3 {k}s: best over 48 signed axis permutations x crop offsets (stride 4), compatible pairs', '',
               '| a | b | identity | best | perm | flips | offset a | offset b |', '|---|---|---|---|---|---|---|---|']
        for s in sorted(out[k]['searched'], key=lambda d: -abs(d['best']['score'])):
            iv = s['identity']['score'] if s['identity'] else None
            b = s['best']
            md.append(f"| `{short(s['a'])}` | `{short(s['b'])}` | {('%.4f' % iv) if iv is not None else 'n/c'} | {b['score']:.4f} | {b['perm']} | {b['flips']} | {b['off_a']} | {b['off_b']} |")
        md.append('')
    (outdir / 'A3_content_level.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
