#!/usr/bin/env python3
"""Copy legacy user banks into the data directory, keeping every source intact."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tracker',ROOT/'application-tracker-skill/scripts/tracker.py')
tracker=importlib.util.module_from_spec(spec);spec.loader.exec_module(tracker)
BANKS={'job-description-skill/jd-bank':'jd-bank','bq-skill/story-bank':'story-bank','offer-compare-skill/offer-bank':'offer-bank','salary-negotiation-skill/deal-bank':'deal-bank'}

def migrate(repo,root,dry_run=False):
    lock=json.loads((repo/'upstreams.lock.json').read_text())
    shipped={f['local_path']:f['installed_sha256'] for s in lock['sources'] for f in s['files']}
    result={'copied':[],'existing':[],'conflicts':[],'excluded_examples':[],'missing_references':[],'dry_run':dry_run}
    for old,bank in BANKS.items():
        if not (repo/old).exists():continue
        index=repo/old/'_index.md'
        if index.is_file() and not index.is_symlink() and shipped.get(str(index.relative_to(repo)))!=hashlib.sha256(index.read_bytes()).hexdigest():
            for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',index.read_text()):
                if '://' in link or link.startswith('#'):continue
                target=(index.parent/link).resolve()
                if not target.exists():
                    result['missing_references'].append({'index':str(index.relative_to(repo)),'link':link})
        for src in sorted((repo/old).rglob('*.md')):
            if src.name.startswith('_') or src.is_symlink():continue
            rel=str(src.relative_to(repo));data=src.read_bytes();sha=hashlib.sha256(data).hexdigest()
            if shipped.get(rel)==sha:
                result['excluded_examples'].append(rel);continue
            dest=root/bank/src.relative_to(repo/old)
            if not dest.resolve().is_relative_to(root.resolve()):raise ValueError('迁移目标越界')
            if dest.exists():
                result['existing' if hashlib.sha256(dest.read_bytes()).hexdigest()==sha else 'conflicts'].append(rel);continue
            if not dry_run:
                tracker.atomic_write(dest,data)
                if hashlib.sha256(dest.read_bytes()).hexdigest()!=sha:raise ValueError('复制校验失败: '+rel)
            result['copied'].append(rel)
    # Generate separate legacy indexes from copied files; never import author example indexes.
    if not dry_run:
        for bank in BANKS.values():
            folder=root/bank
            if folder.exists():
                links=['- ['+p.stem+']('+p.relative_to(folder).as_posix()+')' for p in sorted(folder.rglob('*.md')) if not p.name.startswith('_')]
                target=folder/'_legacy-index.md'
                tracker.atomic_write(target,('# 已迁移旧记录\n\n'+'\n'.join(links)+'\n').encode())
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir');p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    try:
        root=tracker.checked_root(args.data_dir)
        if args.dry_run: result=migrate(ROOT,root,True)
        else:
            with tracker.locked(root):result=migrate(ROOT,root)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['conflicts'] else 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
