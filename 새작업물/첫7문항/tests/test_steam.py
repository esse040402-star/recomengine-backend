import json
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from quick_survey.refresh import fetch
from quick_survey.steam import recommend

class MatchTests(unittest.TestCase):
    def test_api_contract_changes_ranking_and_transfers_price(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                assert self.path=='/api/steam/details?game=a'
                self.send_response(200);self.end_headers()
                self.wfile.write(json.dumps({'details':{'os':{'windows':True},'minimum':[],
                    'price':{'price':120000,'currency':'KRW'},'genres':['전략'],'categoryIds':[9]}}).encode())
            def log_message(self,*args): pass
        with HTTPServer(('127.0.0.1',0),Handler) as http:
            t=Thread(target=http.handle_request);t.start()
            live=fetch('http://127.0.0.1:'+str(http.server_port),'a');t.join()
        row=dict(id='a',app=10,title='A',classification='steam-derived',platforms=['pc'],
                 steamGenres=['액션'],categories=[49],details={})
        weights={'genre:strategy':10,'category:co_op':10,'category:pvp':-10}
        run=lambda u:recommend(weights,{'platforms':['pc']},[row],u)
        self.assertEqual(run({})['games'],[])
        g=run({'a':live})['games'][0]
        self.assertEqual((g['score'],g['price'],g['detail_source']),(20,live['price'],'team_api'))
        self.assertEqual(recommend(weights,{'platforms':['mobile']},[row],{'a':live})['games'],[])
