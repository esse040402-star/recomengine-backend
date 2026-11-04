import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from quick_survey import evaluate
from quick_survey.__main__ import ask,main
ROOT=Path(__file__).resolve().parents[1]
def sample(track='gamer'):return json.loads((ROOT/'examples'/f'{track}.json').read_text())
class LocalTests(unittest.TestCase):
 def test_gamer(self):
  r=evaluate(sample());self.assertEqual(r['weights'],{'category:single_player':10,'genre:action':10,'preference:motion_intensity':-10,'session:short':5,'tag:action':5,'tag:realistic':5});self.assertEqual(r['summary']['axes'],[93,35,50,50,53,10])
 def test_nongamer(self):self.assertEqual(evaluate(sample('nongamer'))['summary']['count'],7)
 def test_no_network(self):
  with patch('socket.socket.connect',side_effect=AssertionError()):self.assertEqual(evaluate(sample())['recommendation']['status'],'matched')
 def test_repeat(self):
  p=sample();before=copy.deepcopy(p);self.assertEqual(evaluate(p),evaluate(p));self.assertEqual(p,before)
 def test_accumulation(self):
  p=sample();p['answers']['q3']=['0','1'];p['answers']['q4']=['2'];p['answers']['q6']=['4'];r=evaluate(p);self.assertEqual(r['weights']['category:pvp'],0);self.assertEqual(r['weights']['genre:strategy'],10);self.assertIn('pvp',r['constraints']['avoid'])
 def test_low_spec(self):
  p=sample('nongamer');p['answers']['q1']=['1'];r=evaluate(p);self.assertEqual(r['weights']['hardware:low_spec'],10);self.assertIsNone(r['constraints']['hardware_spec']);self.assertIsNone(r['constraints']['budget'])
 def test_order(self):
  p=sample();p['answers']['q3']=['1','0'];r=evaluate(p);p['answers']['q3']=['0','1'];self.assertEqual(r['weights'],evaluate(p)['weights'])
 def test_invalid_options(self):
  for q,a in [('q1',['0','1']),('q3',['0','0']),('q3',['0','5']),('q1',['99']),('q2',[]),('q2',[0]),('q2','0')]:
   with self.subTest(q=q,a=a):
    p=sample();p['answers'][q]=a
    with self.assertRaises(ValueError):evaluate(p)
 def test_invalid_payload(self):
  for p in [[],None,{},sample()|{'weights':{}},sample()|{'survey_id':[]},sample()|{'version':'old'},sample()|{'answers':[]}]:
   with self.subTest(p=p),self.assertRaises(ValueError):evaluate(p)
 def test_question_set(self):
  p=sample();del p['answers']['q1']
  with self.assertRaises(ValueError):evaluate(p)
  p=sample();p['answers']['q8']=['0']
  with self.assertRaises(ValueError):evaluate(p)
 def test_interactive(self):
  it=iter(['bad','1','99','1','1','1','1','1','1','1']);self.assertEqual(ask(lambda _:next(it),lambda _:None),sample())
 def test_cli(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'결과.json';r=subprocess.run([sys.executable,'-m','quick_survey',str(ROOT/'examples/gamer.json'),'--output',str(out)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(out.read_text(encoding='utf-8')),evaluate(sample()))
 def test_bad_input_preserves_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.json';p.write_text('{broken');o=Path(d)/'out.json';o.write_text('keep');self.assertEqual(main([str(p),'--output',str(o)]),1);self.assertEqual(o.read_text(),'keep')
 def test_same_file(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text(json.dumps(sample()));self.assertEqual(main([str(p),'--output',str(p)]),1);self.assertEqual(json.loads(p.read_text()),sample())
 def test_large(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text(' '*32769);self.assertEqual(main([str(p)]),1)
 def test_standard_library_only(self):
  r=subprocess.run([sys.executable,'-S','-c','from quick_survey import evaluate; import json; print(evaluate(json.load(open("examples/gamer.json")))["summary"]["count"])'],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'7')
if __name__=='__main__':unittest.main()
