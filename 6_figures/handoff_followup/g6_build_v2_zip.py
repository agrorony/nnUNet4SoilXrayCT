"""Part G: build v2 of the hand-off ZIP from the staging folder and check it.

1. Regenerate <package>/MANIFEST.csv (relative_path,bytes,sha256,source). Unchanged files keep v1's source; changed and
   new files get a follow-up note. v1's manifest is copied to <backup_dir>/MANIFEST_v1.csv first.
2. Write <out_zip> (deflate, ZIP64, every file under '<package name>/', MANIFEST.csv last) and <out_zip>.sha256.
3. Check: testzip() is None; the ZIP's file list = manifest + MANIFEST.csv; all README.md files plus 5 random others
   (seed 20261114) re-extracted and hashed against the manifest.

Usage: python g6_build_v2_zip.py <package_dir> <out_zip> <backup_dir> <evidence_dir>
"""
import csv
import hashlib
import io
import json
import os
import random
import shutil
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB_ZIP = 'lab_data_Schwartz_2026-11.zip (sha256 e8aa566aa304f31ea3c59d951420a2c12308c7e4e194e24efb92e4755c181b1e), extracted at follow-up 2026-11-14'
NOTE = 'see docs/HANDOFF_FOLLOWUP_2026-11.md'


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def sha_stream(f):
    h = hashlib.sha256()
    for b in iter(lambda: f.read(1 << 24), b''):
        h.update(b)
    return h.hexdigest()


def new_source(rel):
    if rel.startswith('07_lab_data_and_writeup/'):
        return LAB_ZIP
    if '/provenance/inference_log_verification_2026-11-10' in rel or '/provenance/otsu_verification_2026-11-10' in rel:
        return f'generated at follow-up 2026-11-10 (Part C verification log; {NOTE})'
    if rel.startswith('04_code/nnUNet4SoilXrayCT_'):
        return f'git archive generated at follow-up 2026-11-14 (commit in 04_code/README.md)'
    if rel.endswith('README.md'):
        return f'written at follow-up 2026-11 ({NOTE})'
    raise ValueError(f'no source rule for new file {rel}')


def main():
    pkg, out, bak, evid = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    assert not out.exists() and not Path(str(out) + '.sha256').exists()
    man = pkg / 'MANIFEST.csv'
    v1 = {r['relative_path']: r for r in csv.DictReader(open(man, encoding='utf-8'))}
    b = bak / 'MANIFEST_v1.csv'
    assert not b.exists()
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(man, b)
    assert sha_file(b) == sha_file(man)

    paths = sorted((Path(d) / f).relative_to(pkg).as_posix() for d, _, fs in os.walk(pkg) for f in fs)
    paths.remove('MANIFEST.csv')
    with ThreadPoolExecutor(8) as ex:
        hashes = dict(zip(paths, ex.map(lambda r: sha_file(pkg / r), paths)))
    rows, kinds = [], dict(unchanged=0, changed=0, added=0)
    for r in paths:
        if r in v1 and v1[r]['sha256'] == hashes[r]:
            src, k = v1[r]['source'], 'unchanged'
        elif r in v1 and r.startswith('07_lab_data_and_writeup/'):
            src, k = LAB_ZIP + ' (replaces the v1 placeholder)', 'changed'
        elif r in v1:
            src, k = f"{v1[r]['source']}; modified at follow-up 2026-11 ({NOTE})", 'changed'
        else:
            src, k = new_source(r), 'added'
        kinds[k] += 1
        rows.append(dict(relative_path=r, bytes=(pkg / r).stat().st_size, sha256=hashes[r], source=src))
    removed = sorted(set(v1) - set(paths) - {'MANIFEST.csv'})
    with open(man, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['relative_path', 'bytes', 'sha256', 'source'])
        w.writeheader()
        w.writerows(rows)
    print(f'manifest: {len(rows)} files ({kinds}); removed vs v1: {len(removed)}', flush=True)

    top = pkg.name + '/'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for i, r in enumerate(paths, 1):
            z.write(pkg / r, top + r)
            if i % 100 == 0:
                print(f'  zipped {i}/{len(paths)}', flush=True)
        z.write(man, top + 'MANIFEST.csv')
    zsha = sha_file(out)
    with open(str(out) + '.sha256', 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'{zsha}  {out.name}\n')
    print('zip written', out.stat().st_size, zsha, flush=True)

    z = zipfile.ZipFile(out)
    bad = z.testzip()
    names = [n for n in z.namelist()]
    list_ok = sorted(names) == sorted([top + r for r in paths] + [top + 'MANIFEST.csv'])
    by = {r['relative_path']: r['sha256'] for r in rows}
    readmes = [r for r in paths if r.endswith('README.md')]
    rnd = random.Random(20261114).sample([r for r in paths if not r.endswith('README.md')], 5)
    checks = []
    for r in readmes + rnd + ['MANIFEST.csv']:
        with z.open(top + r) as f:
            h = sha_stream(f)
        exp = by.get(r, sha_file(man))
        checks.append(dict(path=r, ok=h == exp))
    res = dict(zip=str(out), bytes=out.stat().st_size, sha256=zsha, entries=len(names), files_in_manifest=len(rows),
               content_bytes=sum(r['bytes'] for r in rows), manifest_kinds=kinds, removed_vs_v1=removed,
               testzip=bad, zip_list_equals_manifest=list_ok, n_readmes=len(readmes), random_files=rnd,
               rehash_checked=len(checks), rehash_ok=sum(c['ok'] for c in checks), rehash=checks,
               manifest_v1_backup=str(b))
    json.dump(res, open(evid / 'G6_log.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'rehash'}, indent=1))
    assert bad is None and list_ok and res['rehash_ok'] == len(checks)


if __name__ == '__main__':
    main()
