#!/usr/bin/env python3
"""Local career records. Standard library only; never submits applications."""
import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[2]
STATUSES = {'drafted', 'applied', 'interview', 'offer', 'hired', 'rejected', 'no_response', 'offer_declined', 'withdrawn'}
LABELS = dict(zip(['drafted','applied','interview','offer','hired','rejected','no_response','offer_declined','withdrawn'],
                 ['草稿','已投递','面试','收到 Offer','已接受','被拒绝','无回复','拒绝 Offer','主动撤回']))
FINAL = {'hired','rejected','no_response','offer_declined','withdrawn'}

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')

def safe_id(value):
    if str(uuid.UUID(value)) != value:
        raise ValueError('申请 ID 必须是标准 UUID')
    return value

def checked_root(value=None):
    p = Path(value).expanduser().resolve() if value else REPO / '.career-data'
    if p == REPO or (REPO in p.parents and not p.is_relative_to(REPO / '.career-data')):
        raise ValueError('项目内数据只能放在 .career-data；也可选择项目外目录')
    return p

def empty():
    return {'schema_version': 1, 'revision': 0, 'applications': {}, 'requests': {}}

def validate(db):
    if not isinstance(db, dict) or db.get('schema_version') != 1:
        raise ValueError('不支持的数据格式版本；原文件未修改')
    if type(db.get('revision')) is not int or db['revision'] < 0:
        raise ValueError('损坏的 revision')
    if not isinstance(db.get('applications'), dict) or not isinstance(db.get('requests'), dict):
        raise ValueError('损坏的记录结构')
    for aid, app in db['applications'].items():
        safe_id(aid)
        if not isinstance(app, dict):
            raise ValueError('损坏的申请结构')
        if app.get('id') != aid or app.get('status') not in STATUSES:
            raise ValueError('损坏的申请 ID 或未知状态；不会自动归类为关闭')
        if not isinstance(app.get('events'), list) or not isinstance(app.get('snapshots'), list):
            raise ValueError('损坏的历史结构')
        if not all(isinstance(app.get(k), str) and app[k].strip() for k in ('company','role')):
            raise ValueError('缺少公司或岗位')
        for event in app['events']:
            if not isinstance(event, dict) or event.get('status') not in STATUSES:
                raise ValueError('历史中有未知状态')
        for snapshot in app['snapshots']:
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get('files'), dict):
                raise ValueError('损坏的归档结构')
            for f in snapshot['files'].values():
                if not isinstance(f, dict) or f.get('state') not in {'available','missing'}:
                    raise ValueError('损坏的归档文件')
                if f['state']=='available' and not all(isinstance(f.get(k), str) for k in ('path','sha256')):
                    raise ValueError('损坏的归档路径或校验值')
    for request in db['requests'].values():
        if not isinstance(request, dict) or not isinstance(request.get('signature'), str) or not isinstance(request.get('result'), dict):
            raise ValueError('损坏的操作回执')
    return db

def read(root):
    path = root / 'applications.json'
    if not path.exists():
        return empty()
    if path.is_symlink():
        raise ValueError('数据文件不能是符号链接')
    return validate(json.loads(path.read_text(encoding='utf-8')))

@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.write.lock'
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError('已有写入锁；请核对其他写入或中断现场后再重试，不能自动清锁')
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def text_field(payload, key, required=False):
    value = payload.get(key, '')
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError('无效字段: ' + key)
    return value

def make_snapshot(root, app, materials, request_id):
    """Immutable copies staged before the one JSON commit; return owned directory."""
    if not isinstance(materials, dict) or set(materials) - {'jd','resume','cover_letter'}:
        raise ValueError('materials 只接受 jd/resume/cover_letter 路径')
    snapshot_id = str(uuid.uuid4())
    dest = root / 'applications' / app['id'] / 'submitted' / snapshot_id
    if not dest.resolve().is_relative_to(root.resolve()):
        raise ValueError('归档目标越界')
    dest.mkdir(parents=True, exist_ok=False)
    result = {'id': snapshot_id, 'created_at': now(), 'request_id': request_id, 'files': {}}
    try:
        for kind in ('jd','resume','cover_letter'):
            value = materials.get(kind)
            if value is not None and not isinstance(value, str):
                raise ValueError('材料路径必须是字符串')
            source = Path(value).expanduser().resolve() if value else None
            if not source or not source.is_file():
                result['files'][kind] = {'state': 'missing', 'reason': '未提供或文件不存在'}
                continue
            data = source.read_bytes()
            # A supplied extension is only a display convenience, never a path component.
            suffix = source.suffix if source.suffix.lower() in {'.pdf','.html','.md','.txt','.docx','.tex'} else '.bin'
            target = dest / (kind + suffix)
            atomic_write(target, data)
            if digest(target.read_bytes()) != digest(data):
                raise ValueError('归档校验失败')
            result['files'][kind] = {'state': 'available', 'path': str(target.relative_to(root)), 'sha256': digest(data)}
        return result, dest
    except Exception:
        shutil.rmtree(dest)  # Only this transaction's new directory.
        raise

def mutate(root, operation, payload, request_id, expected_revision):
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError('必须提供稳定 request_id')
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('必须提供读取到的 expected_revision')
    if not isinstance(payload, dict):
        raise ValueError('输入必须是 JSON 对象')
    signature = digest(canonical({'operation':operation,'payload':payload}))
    owned = None
    with locked(root):
        db = read(root)
        old = db['requests'].get(request_id)
        if old:
            if old['signature'] != signature:
                raise ValueError('同一个 request_id 对应不同内容；请先对账')
            return dict(old['result'], replayed=True)
        if db['revision'] != expected_revision:
            raise ValueError('并发冲突：重新读取 revision 后再操作')
        db = copy.deepcopy(db)
        stamp = now()
        if operation == 'create':
            company, role = text_field(payload,'company',True).strip(), text_field(payload,'role',True).strip()
            matches = [a for a in db['applications'].values() if a['company'].casefold()==company.casefold() and a['role'].casefold()==role.casefold()]
            if matches and payload.get('new_attempt') is not True:
                raise ValueError('已有同公司同岗位记录；使用原 ID 或明确 new_attempt=true')
            aid = str(uuid.uuid4())
            drafts = payload.get('materials', {})
            if not isinstance(drafts,dict) or set(drafts)-{'jd','resume','cover_letter'} or not all(isinstance(v,str) for v in drafts.values()):
                raise ValueError('materials 只接受 jd/resume/cover_letter 路径')
            app = {'id':aid, 'company':company, 'role':role, 'status':'drafted',
                   'source_url':text_field(payload,'source_url'), 'created_at':stamp, 'updated_at':stamp,
                   'draft_materials':drafts, 'events':[], 'snapshots':[]}
            db['applications'][aid] = app
            event = {'kind':'created', 'status':'drafted', 'at':stamp, 'note':text_field(payload,'note')}
        else:
            aid = safe_id(text_field(payload,'id',True))
            if aid not in db['applications']:
                raise ValueError('申请不存在')
            app = db['applications'][aid]
            event = {'kind':operation, 'status':app['status'], 'at':stamp, 'note':text_field(payload,'note')}
            if operation in {'status','archive'}:
                if payload.get('confirmed') is not True or not text_field(payload,'evidence',True):
                    raise ValueError('状态/提交材料需用户明确确认，并记录用户原话或回执依据')
                event['evidence'] = payload['evidence']
                event['occurred_on'] = text_field(payload,'occurred_on',True)
                date.fromisoformat(event['occurred_on'])
            if operation == 'status':
                status = payload.get('status')
                if status not in STATUSES or status == 'drafted':
                    raise ValueError('无效状态；不能把已有进度退回草稿')
                if status == app['status']:
                    raise ValueError('状态相同；用 note 追加阶段或反馈')
                if app['status'] in FINAL and payload.get('reopen') is not True:
                    raise ValueError('已关闭；迟到反馈需明确 reopen=true，重新申请请新建记录')
                reached = {e['status'] for e in app['events']}
                if status == 'applied' and reached & {'interview','offer','hired'}:
                    raise ValueError('补投材料请用 archive，不能倒退状态')
                if status == 'interview' and reached & {'offer','hired'} and payload.get('reopen') is not True:
                    raise ValueError('阶段倒退需明确 reopen=true 和依据')
                if status == 'no_response' and not reached & {'applied','interview','offer'}:
                    raise ValueError('未确认投递或接触的草稿不能记为无回复')
                if status in {'hired','offer_declined'} and 'offer' not in reached:
                    raise ValueError('先记录已收到 Offer 的事实')
                event['status'] = status
                app['status'] = status
            elif operation == 'archive':
                if app['status']=='drafted':
                    raise ValueError('草稿尚未投递；确认投递时使用 status=applied')
            elif operation == 'draft':
                materials=payload.get('materials')
                if not isinstance(materials,dict) or set(materials)-{'jd','resume','cover_letter'} or not all(isinstance(v,str) for v in materials.values()):
                    raise ValueError('materials 格式错误')
                app['draft_materials'].update(materials)
            elif operation == 'note':
                event['feedback'] = text_field(payload,'feedback')
                event['suggestion'] = text_field(payload,'suggestion')
                event['stage'] = text_field(payload,'stage')
                if not any(event.get(k) for k in ('note','feedback','suggestion','stage')):
                    raise ValueError('备注不能全空')
            else:
                raise ValueError('未知操作')
        try:
            if operation=='archive' or (operation=='status' and app['status']=='applied'):
                snapshot, owned = make_snapshot(root,app,payload.get('materials',app['draft_materials']),request_id)
                app['snapshots'].append(snapshot)
                event['snapshot_id'] = snapshot['id']
            event['id'] = request_id
            app['events'].append(event)
            app['updated_at'] = stamp
            db['revision'] += 1
            result = {'id':aid,'status':app['status'],'revision':db['revision'],'replayed':False}
            db['requests'][request_id] = {'signature':signature,'result':result}
            validate(db)
            atomic_write(root/'applications.json', canonical(db)+b'\n')
            return result
        except Exception:
            if owned is not None:
                shutil.rmtree(owned)
            raise

def verify_snapshots(root, db):
    root = root.resolve()
    problems=[]
    for app in db['applications'].values():
        for snapshot in app['snapshots']:
            for f in snapshot['files'].values():
                if f['state']!='available': continue
                p=(root/f['path']).resolve()
                if not p.is_relative_to(root) or not p.is_file() or digest(p.read_bytes())!=f['sha256']:
                    problems.append({'id':app['id'],'path':f['path'],'problem':'提交材料缺失或校验不一致'})
    return problems

def summary(db):
    counts={s:0 for s in STATUSES}
    funnel={s:0 for s in ('applied','interview','offer','hired')}
    for app in db['applications'].values():
        counts[app['status']]+=1
        reached={e['status'] for e in app['events']}
        for s in funnel:
            funnel[s]+=int(s in reached)
    return {'current':counts,'reached':funnel}

def render(root):
    db=read(root); problems=verify_snapshots(root,db)
    if problems:
        raise ValueError('归档校验失败：'+json.dumps(problems,ensure_ascii=False))
    stats=summary(db); esc=lambda x:html.escape(str(x),quote=True)
    rows=[]
    for app in sorted(db['applications'].values(),key=lambda a:a['updated_at'],reverse=True):
        kinds={'created':'新建草稿','status':'确认状态','draft':'修改当前材料','archive':'追加提交归档','note':'记录反馈'}
        history='\n'.join(f"{e.get('occurred_on',e['at'])[:10]} · {kinds.get(e['kind'], e['kind'])} · {LABELS[e['status']]} · {e.get('stage','')} {e.get('note','')} {e.get('feedback','')} {e.get('suggestion','')}" for e in app['events'])
        files=[]
        if app['snapshots']:
            for version,snapshot in enumerate(app['snapshots'],1):
                links=[]
                for kind,f in snapshot['files'].items():
                    if f['state']=='available':
                        p=(root/f['path']).resolve()
                        link=quote(os.path.relpath(p, root/'reports'), safe='/')
                        links.append(f'<a href="{esc(link)}">{esc(kind)} · 已提交</a>')
                    else: links.append(esc(kind)+(' · 未提供（可选）' if kind=='cover_letter' else ' · 材料缺失'))
                files.append(f'<details open><summary>提交版本 {version}</summary>'+ '<br>'.join(links)+'</details>')
        else: files.append('尚无提交快照')
        url=app['source_url']
        source=f'<a href="{esc(url)}" rel="noreferrer">原岗位</a>' if url.startswith(('https://','http://')) else '来源待补'
        rows.append(f'<tr data-status="{app["status"]}"><td>{esc(app["company"])}</td><td>{esc(app["role"])}<small>{esc(app["id"])}</small></td><td>{LABELS[app["status"]]}</td><td>{source}<br>'+ '<br>'.join(files)+f'</td><td><details><summary>历史与复盘</summary><pre>{esc(history)}</pre></details></td></tr>')
    options='<option value="">全部状态</option>'+''.join(f'<option value="{s}">{LABELS[s]}</option>' for s in LABELS)
    cards=''.join(f'<article><span>{LABELS[s]} · 曾到达</span><strong>{stats["reached"][s]}</strong></article>' for s in stats['reached'])
    current=' · '.join(LABELS[s]+' '+str(stats['current'][s]) for s in LABELS if stats['current'][s])
    content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>入行求职进展</title><style>
body{font:16px/1.6 system-ui;margin:0;background:#f6f5fa;color:#222}main{max-width:1180px;margin:auto;padding:32px}h1{margin-bottom:0}p{color:#555}.cards{display:flex;gap:16px;flex-wrap:wrap}article{padding:18px;background:white;border-radius:12px;min-width:170px}strong{display:block;font-size:32px;color:#7c3aed}input,select{padding:12px;margin:20px 8px 20px 0;border:1px solid #ccc;border-radius:8px}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:14px;border-bottom:1px solid #eee;vertical-align:top}small{display:block;font-size:10px;color:#777}pre{white-space:pre-wrap;font:inherit}a{color:#6d28d9}.scroll{overflow:auto}footer{margin-top:28px;color:#777}</style><main><h1>求职进展</h1><p>按真实历史统计；草稿不计投递，无回复不等于被拒绝。仅本地读取，修改后重新生成。</p><div class="cards">'''+cards+'</div><input id="search" placeholder="搜索公司、岗位或反馈"><select id="status">'+options+'</select><span id="count"></span><div class="scroll"><table><thead><tr><th>公司</th><th>岗位</th><th>当前状态</th><th>岗位与材料</th><th>进展</th></tr></thead><tbody>'+''.join(rows)+'''</tbody></table></div><footer>入行365 · 方法借鉴 ai-job-search / Mads Lorentzen · 本地资料</footer></main><script>
const rows=[...document.querySelectorAll('tbody tr')];const search=document.getElementById('search'),status=document.getElementById('status');function filter(){let n=0;for(const row of rows){row.hidden=!(row.textContent.toLowerCase().includes(search.value.toLowerCase())&&(!status.value||row.dataset.status===status.value));if(!row.hidden)n++;}document.getElementById('count').textContent=n+' 条';}search.addEventListener('input',filter);status.addEventListener('change',filter);filter();</script></html>'''
    content=content.replace('<div class="cards">','<p>全量记录当前状态：'+esc(current or '暂无记录')+'。筛选只改变下方列表。</p><div class="cards">')
    content=content.replace('<input id="search"', '<input aria-label="搜索投递记录" id="search"').replace('<select id="status"', '<select aria-label="按状态筛选" id="status"')
    content=content.replace('</style>', 'table{min-width:900px}th{white-space:nowrap}td:nth-child(3){white-space:nowrap}td:last-child{min-width:280px}small{overflow-wrap:anywhere}@media(max-width:600px){main{padding:20px}.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}article{min-width:0;padding:12px}}</style>')
    target=root/'reports'/'applications.html'
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('报告目标越界')
    atomic_write(target,content.encode('utf-8'))
    return {'report':str(target),'summary':stats,'revision':db['revision']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['read','create','status','draft','archive','note','report','verify'])
    p.add_argument('--data-dir'); p.add_argument('--input',help='JSON 输入文件，避免在命令行暴露个人内容')
    p.add_argument('--request-id');p.add_argument('--expected-revision',type=int)
    args=p.parse_args()
    try:
        root=checked_root(args.data_dir)
        if args.operation=='read': result=read(root)
        elif args.operation=='report': result=render(root)
        elif args.operation=='verify':
            result={'problems':verify_snapshots(root,read(root))}
            if result['problems']:
                print(json.dumps(result,ensure_ascii=False));return 1
        else:
            if not args.input: raise ValueError('需要 --input JSON 文件')
            result=mutate(root,args.operation,json.loads(Path(args.input).read_text(encoding='utf-8')),args.request_id,args.expected_revision)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc),'written':False},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__': sys.exit(main())
