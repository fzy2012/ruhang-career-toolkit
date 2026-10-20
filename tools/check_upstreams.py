#!/usr/bin/env python3
"""Read-only upstream diff. No fetch/merge/install or tracked-file writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def sha(data): return hashlib.sha256(data).hexdigest()

def api(path):
    proc=subprocess.run(['gh','api',path],capture_output=True,text=True,timeout=60)
    if proc.returncode: raise RuntimeError('GitHub 读取失败: '+path+' (exit '+str(proc.returncode)+')')
    return json.loads(proc.stdout)

def in_scope(path, scopes):
    return any(path==s or path.startswith(s+'/') for s in scopes)

def local_file(root, rel):
    target=(root/rel).resolve()
    if not target.is_relative_to(root.resolve()): raise ValueError('锁定清单包含越界路径')
    return sha(target.read_bytes()) if target.is_file() else None

def compare(source, candidate, root):
    changes=[]; known=set()
    for f in source['files']:
        path=f['source_path'];known.add(path)
        current=local_file(root,f['local_path']);new=candidate.get(path)
        drift=current!=f['installed_sha256']
        upstream_changed=new!=f['upstream_blob']
        if upstream_changed or drift:
            change='deleted' if new is None else 'modified'
            changes.append({'source_path':path,'local_path':f['local_path'],
                'upstream':change if upstream_changed else 'unchanged',
                'local_drift':drift,'local_adapted':current!=f['upstream_sha256'],
                'review_conflict':upstream_changed and current!=f['upstream_sha256'],
                'adaptation_review':source.get('adaptation_paths',[]) if upstream_changed else []})
    for path in sorted(candidate):
        if path not in known and in_scope(path,source['scopes']):
            changes.append({'source_path':path,'upstream':'added','review_conflict':False})
    return changes

def run(root=ROOT, local_only=False, fetch=api, refs=None):
    lock=json.loads((root/'upstreams.lock.json').read_text())
    if lock.get('schema_version')!=1: raise ValueError('未知清单版本')
    result={'complete':True,'read_only':True,'sources':[],'legacy_files':[]}
    for f in lock.get('legacy_files',[]):
        valid=local_file(root,f['local_path'])==f['installed_sha256']
        result['legacy_files'].append({'path':f['local_path'],'valid':valid})
        if not valid: result['complete']=False
    for source in lock['sources']:
        row={'id':source['id'],'baseline':source['commit']}
        try:
            row['adaptation_drift']=[f['path'] for f in source.get('adaptations',[]) if local_file(root,f['path'])!=f['sha256']]
            if local_only and row['adaptation_drift']: result['complete']=False
            if local_only:
                row['drift']=[f['local_path'] for f in source['files'] if local_file(root,f['local_path'])!=f['installed_sha256']]
                if row['drift']:result['complete']=False
            else:
                repo=source['repository']
                if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo):raise ValueError('无效仓库')
                ref=(refs or {}).get(source['id'])
                if ref is None:
                    ref=fetch('repos/'+repo+'/releases/latest')['tag_name'] if source['release'] else fetch('repos/'+repo)['default_branch']
                if not re.fullmatch(r'[\w./-]+',ref):raise ValueError('无效候选版本')
                commit=fetch('repos/'+repo+'/commits/'+ref)['sha']
                tree=fetch('repos/'+repo+'/git/trees/'+commit+'?recursive=1')
                if tree.get('truncated'):raise ValueError('上游目录被截断，检查不完整')
                candidate={f['path']:f['sha'] for f in tree['tree'] if f['type']=='blob'}
                row.update(candidate=commit,reference=ref,changes=compare(source,candidate,root))
            row['checked']=True
        except (RuntimeError,ValueError,OSError,KeyError,subprocess.TimeoutExpired) as exc:
            row.update(checked=False,error=str(exc));result['complete']=False
        result['sources'].append(row)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-local',action='store_true')
    p.add_argument('--offer-ref');p.add_argument('--job-ref');args=p.parse_args()
    try:
        result=run(local_only=args.verify_local,refs={k:v for k,v in {'offer':args.offer_ref,'job':args.job_ref}.items() if v})
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['complete'] else 2
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'complete':False,'error':str(exc)},ensure_ascii=False));return 2
if __name__=='__main__':sys.exit(main())
