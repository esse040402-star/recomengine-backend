import unittest,tempfile,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'구현코드'))
from personal import PersonalStore
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3';self.catalog=json.loads(Path(__file__).with_name('catalog_fixture.json').read_text(encoding='utf-8'));self.store=PersonalStore(self.path,self.catalog)
 def tearDown(self):self.tmp.cleanup()
 def survey(self,id='s1',owner='a'):
  self.store.record_survey(owner,{'result_id':id,'summary':{'title':'탐험가','count':7,'evidence':[]},'weights':{'tag:open_world':10}})
  return self.store.update(owner,'profiles',{'name':'탐험가','survey':id})
 def test_empty(self):self.assertEqual(self.store.state('a')['profiles'],[])
 def test_profile_weight(self):self.assertEqual(self.survey()['profiles'][0]['weights'],{'tag:open_world':10})
 def test_latest_active(self):
  self.survey();s=self.survey('s2');self.assertEqual(s['settings']['active'],s['profiles'][-1]['id'])
 def test_cross_owner(self):
  p=self.survey()['profiles'][0]
  with self.assertRaises(ValueError):self.store.update('b','active',{'id':p['id']})
  with self.assertRaises(ValueError):self.store.record_survey('b',{'result_id':'s1'})
 def test_repeat_profile(self):
  self.survey()
  with self.assertRaises(ValueError):self.store.update('a','profiles',{'name':'중복','survey':'s1'})
 def test_wishlist(self):
  for _ in range(2):self.store.update('a','wishlist',{'game':'elden','saved':True})
  self.assertEqual(len(self.store.state('a')['wishlist']),1)
  self.store.update('a','wishlist',{'game':'elden','saved':False});self.assertEqual(self.store.state('a')['wishlist'],[])
 def test_recent(self):
  for _ in range(2):self.store.update('a','recent',{'game':'elden'})
  self.assertEqual(len(self.store.state('a')['recent']),1)
 def test_persist(self):
  self.store.update('a','settings',{'nickname':'테스터','bio':'소개','theme':'elden','avatar':'Rocket','cover_y':80,'cover_shade':20})
  s=PersonalStore(self.path,self.catalog).state('a')['settings'];self.assertEqual(s['cover_y'],80);self.assertEqual(s['avatar'],'Rocket')
 def test_invalid(self):
  for action,p in [('recent',{'game':[]}),('settings',{'nickname':'a','theme':[]}),('settings',{'nickname':'a','theme':'elden','cover_y':101})]:
   with self.assertRaises(ValueError):self.store.update('a',action,p)
if __name__=='__main__':unittest.main()
