"""Loopback-only test harness. Python standard library, no external service."""
import argparse
import json
import re
from urllib.parse import unquote, urlsplit
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import threading
from uuid import UUID
import webbrowser
from .service import evaluate
from .scoring import definition
from .__main__ import write_json

ROOT=Path(__file__).resolve().parents[1]

def create_server(port=0, directory=None):
    results=Path(directory) if directory else ROOT/'results'
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,data,content_type='application/json; charset=utf-8'):
            body=json.dumps(data,ensure_ascii=False).encode() if content_type.startswith('application/json') else data.encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def allowed(self):
            host=self.headers.get('Host','')
            return host in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def load(self,rid):
            rid=str(UUID(rid));return json.loads((results/(rid+'.json')).read_text(encoding='utf-8'))
        def do_GET(self):
            if not self.allowed():return self.reply(403,{'detail':'허용되지 않은 주소입니다.'})
            requested_path=unquote(urlsplit(self.path).path)
            if requested_path.startswith('/미리보기/'):
                filename=requested_path[len('/미리보기/'):]
                if not re.fullmatch(r'미리보기_\d{2}\.js',filename):
                    return self.reply(404,{'detail':'찾을 수 없습니다.'})
                file=ROOT/'frontend'/'미리보기'/filename
                if not file.is_file():return self.reply(404,{'detail':'찾을 수 없습니다.'})
                return self.reply(200,file.read_text(encoding='utf-8'),'text/javascript; charset=utf-8')
            try:
                if self.path=='/':
                    path=ROOT/'frontend/화면_최종.html'
                    return self.reply(200,path.read_text(encoding='utf-8'),'text/html; charset=utf-8') if path.exists() else self.reply(200,{'message':'백엔드 전용 패키지입니다.'})
                if self.path=='/health':return self.reply(200,{'status':'ok'})
                if self.path.startswith('/api/quick-survey/definitions/'):
                    return self.reply(200,definition(self.path.rsplit('/',1)[1]))
                if self.path.startswith('/api/quick-survey/results/'):
                    return self.reply(200,self.load(self.path.rsplit('/',1)[1]))
                if self.path.startswith('/saved/'):
                    import html
                    data=self.load(self.path.rsplit('/',1)[1])
                    answers='\n\n'.join(x['question']+'\n→ '+x['answer'] for x in data['summary']['evidence'])
                    scores='\n'.join(k+': '+str(v) for k,v in data['weights'].items())
                    games=data.get('recommendation',{}).get('games') or []
                    ranked='<ol>'+''.join('<li>'+html.escape(g['title'])+' · '+str(g['score'])+'점</li>' for g in games)+'</ol>' if games else '<p>일치하는 게임이 없습니다.</p>'
                    return self.reply(200,'<!doctype html><meta charset="utf-8"><title>Python 저장 결과</title><style>body{max-width:1000px;margin:48px auto;padding:0 24px;font:17px/1.7 sans-serif;color:#18243b}pre{white-space:pre-wrap;background:#f2f5fa;padding:24px;border-radius:16px}a{color:#365fee}</style><h1>Python 계산 · 파일 저장 완료</h1><p>아래 내용은 저장된 JSON 파일을 다시 읽은 결과입니다.</p><p>파일: results/'+html.escape(data['result_id'])+'.json</p><h2>'+html.escape(data['summary']['title'])+'</h2><h2>선택한 응답</h2><pre>'+html.escape(answers)+'</pre><h2>최종 가중치</h2><pre>'+html.escape(scores)+'</pre><h2>추천 게임</h2>'+ranked+'<a href="/api/quick-survey/results/'+data['result_id']+'">저장된 전체 JSON 보기</a>','text/html; charset=utf-8')
                return self.reply(404,{'detail':'찾을 수 없습니다.'})
            except (ValueError,FileNotFoundError):return self.reply(404,{'detail':'결과 또는 설문을 찾을 수 없습니다.'})
            except OSError:return self.reply(500,{'detail':'파일을 읽지 못했습니다.'})
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.allowed() or self.headers.get('Sec-Fetch-Site')=='cross-site' or (origin and origin!='http://'+self.headers['Host']):return self.reply(403,{'detail':'같은 로컬 화면에서 제출해주세요.'})
            if self.path!='/api/quick-survey/submissions':return self.reply(404,{'detail':'찾을 수 없습니다.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=32768:return self.reply(413,{'detail':'응답 크기를 확인해주세요.'})
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError('응답 형식 오류')
                rid=str(UUID(payload.pop('submission_id','')))
                data=evaluate(payload)
                path=results/(rid+'.json')
                if path.exists():
                    old=self.load(rid)
                    if any(old[k]!=data[k] for k in ['survey_id','version','answers']):return self.reply(409,{'detail':'제출 ID가 중복되었습니다. 설문을 다시 시작해주세요.'})
                    return self.reply(200,old)
                data.update(result_id=rid,saved=True)
                write_json(path,data)
                return self.reply(200,self.load(rid))
            except (ValueError,TypeError):return self.reply(422,{'detail':'질문별 선택 내용과 설문 버전을 확인해주세요.'})
            except OSError:return self.reply(500,{'detail':'결과를 저장하지 못했습니다. 폴더 쓰기 권한을 확인해주세요.'})
    return HTTPServer(('127.0.0.1',port),Handler)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    with create_server(args.port) as server:
        url=f'http://127.0.0.1:{server.server_port}/'
        print('브라우저에서 설문을 진행해주세요:',url,flush=True)
        print('이 창을 켜두세요. 종료: Ctrl+C',flush=True)
        if not args.no_browser:threading.Timer(.4,lambda:webbrowser.open(url)).start()
        try:server.serve_forever()
        except KeyboardInterrupt:pass
    return 0
if __name__=='__main__':raise SystemExit(main())
