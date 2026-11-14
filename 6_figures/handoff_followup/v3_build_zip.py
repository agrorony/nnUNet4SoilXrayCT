"""Package v3, last step: MANIFEST.csv, the ZIP, its .sha256, and the checks.

MANIFEST.csv: relative_path, bytes, sha256, source. Source = the v2 package path (or "repo main: <path>") the file was
copied from (v3_copy_log.json), "written for v3" for READMEs, or the git-archive commit for the code archive.
Checks: testzip() is None; the ZIP's file list = MANIFEST.csv + MANIFEST.csv itself; all README.md files plus 5 random
other files (seed 20261114) and MANIFEST.csv re-extracted and hashed.

Usage: python v3_build_zip.py <v3_package_dir> <out_zip> <copy_log_json> <code_archive_log_json> <log_json>
"""
import csv
import hashlib
import json
import os
import random
import sys
import zipfile
from pathlib import Path


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


def main():
    pkg, out, copy_log, code_log, log_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    assert not out.exists() and not Path(str(out) + '.sha256').exists() and not (pkg / 'MANIFEST.csv').exists()
    copied = json.load(open(copy_log))['copied']
    code = json.load(open(code_log))
    code_rel = Path(code['archive']).relative_to(pkg).as_posix()
    paths = sorted((Path(d) / f).relative_to(pkg).as_posix() for d, _, fs in os.walk(pkg) for f in fs)
    rows = []
    for r in paths:
        p = pkg / r
        h = sha_file(p)
        if r in copied:
            assert copied[r]['sha256'] == h, r
            src = copied[r]['source']
            src = 'repo main: ' + src[5:] if src.startswith('REPO:') else 'v2 package: ' + src
        elif r == code_rel:
            assert code['sha256'] == h
            src = f"git archive of repo main, commit {code['commit']}"
        elif r.endswith('README.md'):
            src = 'written for v3 (see PACKAGE_MAP_v2_to_v3.csv)'
        else:
            raise ValueError(f'unknown source for {r}')
        rows.append(dict(relative_path=r, bytes=p.stat().st_size, sha256=h, source=src))
    man = pkg / 'MANIFEST.csv'
    with open(man, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['relative_path', 'bytes', 'sha256', 'source'])
        w.writeheader()
        w.writerows(rows)
    print(f'manifest: {len(rows)} files, {sum(r["bytes"] for r in rows) / 1e9:.3f} GB', flush=True)

    top = pkg.name + '/'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for i, r in enumerate(paths, 1):
            z.write(pkg / r, top + r)
            if i % 25 == 0:
                print(f'  zipped {i}/{len(paths)}', flush=True)
        z.write(man, top + 'MANIFEST.csv')
    zsha = sha_file(out)
    with open(str(out) + '.sha256', 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'{zsha}  {out.name}\n')
    print('zip written', out.stat().st_size, zsha, flush=True)

    z = zipfile.ZipFile(out)
    bad = z.testzip()
    names = z.namelist()
    list_ok = sorted(names) == sorted([top + r for r in paths] + [top + 'MANIFEST.csv'])
    by = {r['relative_path']: r['sha256'] for r in rows}
    by['MANIFEST.csv'] = sha_file(man)
    readmes = [r for r in paths if r.endswith('README.md')]
    rnd = random.Random(20261114).sample([r for r in paths if not r.endswith('README.md')], 5)
    checks = []
    for r in readmes + rnd + ['MANIFEST.csv']:
        with z.open(top + r) as f:
            checks.append(dict(path=r, ok=sha_stream(f) == by[r]))
    res = dict(zip=str(out), bytes=out.stat().st_size, sha256=zsha, entries=len(names), files_in_manifest=len(rows),
               content_bytes=sum(r['bytes'] for r in rows), testzip=bad, zip_list_equals_manifest=list_ok,
               n_readmes=len(readmes), random_files=rnd, rehash_checked=len(checks), rehash_ok=sum(c['ok'] for c in checks),
               rehash=checks, code_archive_commit=code['commit'])
    json.dump(res, open(log_json, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'rehash'}, indent=1))
    assert bad is None and list_ok and res['rehash_ok'] == len(checks)


if __name__ == '__main__':
    main()
