import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
T=load('tracker','application-tracker-skill/scripts/tracker.py')
U=load('upstreams','tools/check_upstreams.py')
M=load('migrate','tools/migrate_legacy.py')

class TrackerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'data';self.n=0
 def write(self,op,payload,key=None,revision=None):
  self.n+=1
  return T.mutate(self.root,op,payload,key or str(self.n),T.read(self.root)['revision'] if revision is None else revision)
 def create(self,**extra):return self.write('create',{'company':'示例 <公司>','role':'产品经理',**extra})['id']
 def status(self,aid,status,**extra):return self.write('status',{'id':aid,'status':status,'confirmed':True,'evidence':'合成验收用户明确报告','occurred_on':'2026-10-20',**extra})
 def test_read_has_no_side_effect(self):
  self.assertEqual(T.read(self.root)['revision'],0);self.assertFalse(self.root.exists())
 def test_idempotency_and_collision(self):
  p={'company':'A','role':'B'};a=self.write('create',p,key='stable');b=self.write('create',p,key='stable',revision=0)
  self.assertEqual(a['id'],b['id']);self.assertTrue(b['replayed']);self.assertEqual(T.read(self.root)['revision'],1)
  with self.assertRaises(ValueError):self.write('create',{'company':'C','role':'B'},key='stable')
 def test_repeat_application_needs_explicit_new_attempt(self):
  first=self.create()
  with self.assertRaises(ValueError):self.create()
  second=self.create(new_attempt=True);self.assertNotEqual(first,second);self.assertEqual(len(T.read(self.root)['applications']),2)
 def test_revision_conflict(self):
  self.create();before=(self.root/'applications.json').read_bytes()
  with self.assertRaises(ValueError):self.write('create',{'company':'B','role':'C'},revision=0)
  self.assertEqual((self.root/'applications.json').read_bytes(),before)
 def test_lock_not_removed_by_competitor(self):
  self.root.mkdir();(self.root/'.write.lock').write_text('other')
  with self.assertRaises(ValueError):self.create()
  self.assertTrue((self.root/'.write.lock').exists())
 def test_corruption_fail_closed(self):
  self.root.mkdir();p=self.root/'applications.json';p.write_text('{bad')
  with self.assertRaises(ValueError):self.create()
  self.assertEqual(p.read_text(),'{bad')
 def test_unknown_status_fail_closed(self):
  aid=self.create();db=T.read(self.root);db['applications'][aid]['status']='mystery';p=self.root/'applications.json';p.write_text(json.dumps(db));before=p.read_bytes()
  with self.assertRaises(ValueError):self.write('note',{'id':aid,'note':'test'})
  self.assertEqual(p.read_bytes(),before)
 def test_confirmation_required(self):
  aid=self.create()
  with self.assertRaises(ValueError):self.write('status',{'id':aid,'status':'applied'})
  self.assertEqual(T.read(self.root)['applications'][aid]['status'],'drafted')
 def test_draft_not_silent(self):
  aid=self.create()
  with self.assertRaises(ValueError):self.status(aid,'no_response')
  self.assertEqual(T.summary(T.read(self.root))['reached']['applied'],0)
 def test_snapshot_immutable_and_missing_explicit(self):
  src=Path(self.tmp.name)/'resume.html';src.write_text('version one');aid=self.create(materials={'resume':str(src)})
  self.status(aid,'applied');src.write_text('version two')
  app=T.read(self.root)['applications'][aid];snap=app['snapshots'][0]['files']
  self.assertEqual((self.root/snap['resume']['path']).read_text(),'version one');self.assertEqual(snap['jd']['state'],'missing')
  self.write('archive',{'id':aid,'confirmed':True,'evidence':'明确补投','occurred_on':'2026-10-20','materials':{'resume':str(src)}})
  app=T.read(self.root)['applications'][aid];self.assertEqual(len(app['snapshots']),2);self.assertEqual(T.verify_snapshots(self.root,T.read(self.root)),[])
 def test_failed_save_keeps_previous_record_and_no_snapshot(self):
  aid=self.create();before=(self.root/'applications.json').read_bytes();original=T.atomic_write
  def fail(path,data):
   if path.name=='applications.json':raise OSError('disk failure')
   return original(path,data)
  with patch.object(T,'atomic_write',side_effect=fail):
   with self.assertRaises(OSError):self.status(aid,'applied')
  self.assertEqual((self.root/'applications.json').read_bytes(),before)
  self.assertFalse(list(self.root.glob('applications/*/submitted/*')))
 def test_failed_replace_keeps_old_json(self):
  aid=self.create();before=(self.root/'applications.json').read_bytes()
  with patch.object(T.os,'replace',side_effect=OSError('cannot replace')):
   with self.assertRaises(OSError):self.write('note',{'id':aid,'note':'save me'})
  self.assertEqual((self.root/'applications.json').read_bytes(),before);self.assertFalse(list(self.root.glob('.pending-*')))
 def test_history_funnel_not_current_status(self):
  aid=self.create();self.status(aid,'applied');self.status(aid,'interview');self.status(aid,'rejected')
  stats=T.summary(T.read(self.root));self.assertEqual(stats['reached'],{'applied':1,'interview':1,'offer':0,'hired':0})
  self.assertEqual(stats['current']['rejected'],1)
 def test_offer_does_not_invent_interview(self):
  aid=self.create();self.status(aid,'offer');self.status(aid,'hired')
  stats=T.summary(T.read(self.root));self.assertEqual(stats['reached']['interview'],0);self.assertEqual(stats['reached']['applied'],0)
 def test_closed_requires_reopen_or_new_attempt(self):
  aid=self.create();self.status(aid,'rejected')
  with self.assertRaises(ValueError):self.status(aid,'interview')
  self.status(aid,'interview',reopen=True);self.assertEqual(len(T.read(self.root)['applications'][aid]['events']),3)
 def test_report_escapes_and_no_remote_dependencies(self):
  aid=self.create(source_url='javascript:alert(1)');self.write('note',{'id':aid,'feedback':'<script>alert(1)</script>','suggestion':'候选建议'})
  report=Path(T.render(self.root)['report']).read_text()
  self.assertIn('&lt;script&gt;',report);self.assertNotIn('<script>alert(1)</script>',report);self.assertNotIn('href="javascript:',report);self.assertNotIn('<script src=',report)
 def test_tampered_snapshot_stops_report(self):
  src=Path(self.tmp.name)/'r.md';src.write_text('test');aid=self.create(materials={'resume':str(src)});self.status(aid,'applied')
  snap=T.read(self.root)['applications'][aid]['snapshots'][0]['files']['resume'];(self.root/snap['path']).write_text('changed')
  self.assertEqual(len(T.verify_snapshots(self.root,T.read(self.root))),1)
  with self.assertRaises(ValueError):T.render(self.root)
 def test_source_directory_rejected(self):
  with self.assertRaises(ValueError):T.checked_root(ROOT/'resume-skill')
 def test_nested_corruption_fails_without_write(self):
  aid=self.create();db=T.read(self.root);db['applications'][aid]['snapshots']=[{'files':{'resume':None}}]
  p=self.root/'applications.json';p.write_text(json.dumps(db));before=p.read_bytes()
  with self.assertRaises(ValueError):self.write('note',{'id':aid,'note':'test'})
  self.assertEqual(p.read_bytes(),before)
 def test_archive_symlink_escape_rejected(self):
  aid=self.create();outside=Path(self.tmp.name)/'outside';outside.mkdir()
  (self.root/'applications').symlink_to(outside,target_is_directory=True)
  with self.assertRaises(ValueError):self.status(aid,'applied')
  self.assertEqual(list(outside.iterdir()),[]);self.assertEqual(T.read(self.root)['revision'],1)
 def test_whitespace_does_not_bypass_duplicate_check(self):
  self.create()
  with self.assertRaises(ValueError):self.create(company='  示例 <公司>  ')
 def test_declining_offer_requires_offer_history(self):
  aid=self.create()
  with self.assertRaises(ValueError):self.status(aid,'offer_declined')
  self.status(aid,'offer');self.status(aid,'offer_declined')
  self.assertEqual(T.summary(T.read(self.root))['current']['offer_declined'],1)
 def test_newer_schema_is_preserved(self):
  self.root.mkdir();p=self.root/'applications.json';p.write_text('{"schema_version":99}')
  with self.assertRaises(ValueError):self.create()
  self.assertEqual(p.read_text(),'{"schema_version":99}')
 def test_two_writers_only_one_commits(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  self.root.mkdir();barrier=Barrier(2)
  def attempt(i):
   barrier.wait()
   try:return T.mutate(self.root,'create',{'company':str(i),'role':'Designer'},str(i),0)
   except ValueError:return None
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[1,2]))
  self.assertEqual(sum(r is not None for r in results),1)
  self.assertEqual(T.read(self.root)['revision'],1)

class UpgradeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def source(self):
  (self.root/'local.md').write_bytes(b'base');return {'scopes':['module'],'files':[{'source_path':'module/a.md','local_path':'local.md','upstream_sha256':U.sha(b'base'),'installed_sha256':U.sha(b'base'),'upstream_blob':'old'}]}
 def test_rename_reports_delete_add_without_write(self):
  s=self.source();r=U.compare(s,{'module/new.md':'new'},self.root)
  self.assertEqual([x['upstream'] for x in r],['deleted','added']);self.assertEqual((self.root/'local.md').read_bytes(),b'base')
 def test_local_change_and_upstream_conflict(self):
  s=self.source();(self.root/'local.md').write_bytes(b'local');r=U.compare(s,{'module/a.md':'new'},self.root)
  self.assertTrue(r[0]['review_conflict']);self.assertTrue(r[0]['local_drift'])
 def test_network_error_is_incomplete(self):
  s=self.source();s.update(id='offer',repository='owner/repo',commit='x',release=None)
  (self.root/'upstreams.lock.json').write_text(json.dumps({'schema_version':1,'sources':[s]}))
  def fail(path):raise RuntimeError('offline')
  self.assertFalse(U.run(self.root,fetch=fail)['complete'])
 def test_copy_migration_preserves_source_and_excludes_examples(self):
  old=self.root/'bq-skill/story-bank';old.mkdir(parents=True);(old/'example.md').write_text('example');(old/'real.md').write_text('真实经历')
  (self.root/'upstreams.lock.json').write_text(json.dumps({'sources':[{'files':[{'local_path':'bq-skill/story-bank/example.md','installed_sha256':U.sha(b'example')}]}]}))
  data=self.root/'data';r=M.migrate(self.root,data);self.assertEqual(len(r['copied']),1);self.assertTrue((old/'real.md').exists());self.assertFalse((data/'story-bank/example.md').exists())
  (old/'real.md').write_text('改动');r=M.migrate(self.root,data);self.assertEqual(len(r['conflicts']),1);self.assertEqual((data/'story-bank/real.md').read_text(),'真实经历')
 def test_dry_migration_does_not_create_data(self):
  (self.root/'upstreams.lock.json').write_text('{"sources":[]}');data=self.root/'data';M.migrate(self.root,data,True);self.assertFalse(data.exists())
 def test_missing_legacy_record_reported_not_fabricated(self):
  folder=self.root/'bq-skill/story-bank';folder.mkdir(parents=True)
  (folder/'_index.md').write_text('[旧经历](missing.md)')
  (self.root/'upstreams.lock.json').write_text('{"sources":[]}')
  data=self.root/'data';result=M.migrate(self.root,data,True)
  self.assertEqual(result['missing_references'][0]['link'],'missing.md');self.assertFalse(data.exists())

if __name__=='__main__':unittest.main()
