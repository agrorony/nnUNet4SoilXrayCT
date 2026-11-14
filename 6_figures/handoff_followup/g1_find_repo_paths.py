"""Part G prep (read-only): find repo paths cited in the package's Markdown files that the 2026-11 restructure moved.

A citation is any backticked token, or markdown link target, that equals an old path in archive/PATH_MAP_2026-11.csv,
or is a directory prefix of old paths (e.g. `06_reporting/missing_data_20261004/`). For each, the new path is
proposed (directory prefixes: the common new prefix of all files under it, if there is one).

Usage: python g1_find_repo_paths.py <repo_dir> <package_dir> <out_json>
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

TOKEN = re.compile(r'`([^`\n]+)`|\]\(([^)\s]+)\)')


def main():
    repo, pkg, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    pm = {r['old_path']: r['new_path'] for r in csv.DictReader(open(repo / 'archive/PATH_MAP_2026-11.csv', encoding='utf-8'))}
    olds = list(pm)

    def lookup(tok):
        t = tok.strip().replace('\\', '/').lstrip('./')
        if t in pm:
            return dict(kind='file', new=pm[t])
        d = t.rstrip('/') + '/'
        under = [o for o in olds if o.startswith(d)]
        if under:
            news = [pm[o] for o in under if not pm[o].startswith('(')]
            common = os.path.commonpath(news).replace('\\', '/') if news else None
            # map the directory only if every file under it moved to the same relative place
            rel_ok = common and all(pm[o] == common + '/' + o[len(d):] for o in under if not pm[o].startswith('('))
            return dict(kind='dir', n_files=len(under), new=(common + '/') if rel_ok else None,
                        removed=sum(pm[o].startswith('(') for o in under), example=[under[0], pm[under[0]]])
        return None

    hits = []
    for md in sorted(pkg.rglob('*.md')):
        rel = md.relative_to(pkg).as_posix()
        for ln_no, line in enumerate(md.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            for m in TOKEN.finditer(line):
                tok = m.group(1) or m.group(2)
                if '/' not in tok and '\\' not in tok and tok not in ('RESOURCES.md', 'DATA_CATALOG.md', 'README.md', 'PROJECT_STATUS.md'):
                    continue
                r = lookup(tok)
                if r is None and tok in ('RESOURCES.md', 'PROJECT_STATUS.md'):
                    r = lookup('00_docs/' + tok) or lookup('00_docs/reports/' + tok)
                if r:
                    hits.append(dict(file=rel, line=ln_no, token=tok, **r, context=line.strip()[:200]))
    json.dump(hits, open(out, 'w'), indent=1)
    by_tok = {}
    for h in hits:
        by_tok.setdefault((h['token'], h.get('new')), []).append(f"{h['file']}:{h['line']}")
    for (tok, new), where in sorted(by_tok.items(), key=lambda kv: kv[0][0]):
        print(f"{tok}  ->  {new}   [{len(where)}x] e.g. {where[0]}")
    print(len(hits), 'citations in', len({h['file'] for h in hits}), 'files')


if __name__ == '__main__':
    main()
