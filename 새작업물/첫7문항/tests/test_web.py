import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from uuid import uuid4
from quick_survey.local_web import create_server
class WebTest(unittest.TestCase):
 def test_submit_persist_read_and_retry(self):
  with tempfile.TemporaryDirectory() as d:
   server=create_server(directory=d);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
   try:
    for track in ['gamer','nongamer']:
     with urllib.request.urlopen(base+'/api/quick-survey/definitions/'+track) as r:definition=json.load(r)
     payload={'survey_id':definition['survey_id'],'version':definition['version'],'submission_id':str(uuid4()),'answers':{q['id']:['0'] for q in definition['questions']}}
     def post():
      req=urllib.request.Request(base+'/api/quick-survey/submissions',json.dumps(payload).encode(),{'Content-Type':'application/json','Origin':base})
      with urllib.request.urlopen(req) as r:return json.load(r)
     result=post();self.assertEqual(result,post())
     self.assertEqual(result,json.loads((Path(d)/(result['result_id']+'.json')).read_text(encoding='utf-8')))
     with urllib.request.urlopen(base+'/saved/'+result['result_id']) as r:self.assertIn('최종 가중치',r.read().decode())
     payload['answers']['q1']=['99']
     with self.assertRaises(urllib.error.HTTPError) as exc:post()
     self.assertEqual(exc.exception.code,422)
   finally:server.shutdown();thread.join();server.server_close()
