"""python -m quick_survey [answers.json] --output result.json"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .scoring import QUESTIONS, VERSION
from .service import evaluate

def ask(input_fn=input, output_fn=print):
    while True:
        choice=input_fn('설문 선택: 1. 게이머 / 2. 비게이머 > ').strip()
        if choice in ('1','2'): break
        output_fn('1 또는 2를 입력해주세요.')
    track='gamer' if choice=='1' else 'nongamer'
    answers={}
    for number,q in enumerate(QUESTIONS[track],1):
        output_fn(f"\n[{number}/7] {q['title']} (최대 {q['max']}개)")
        for i,o in enumerate(q['options'],1):output_fn(f"  {i}. {o['label']}")
        while True:
            raw=input_fn('선택 번호 (여러 개는 쉼표로 구분) > ').strip()
            try:
                indices=[int(s.strip())-1 for s in raw.split(',')]
                if not 1<=len(indices)<=q['max'] or len(indices)!=len(set(indices)) or any(i<0 or i>=len(q['options']) for i in indices):raise ValueError()
                chosen=[q['options'][i] for i in indices]
                if len(chosen)>1 and any(o['prefs'].get('none') for o in chosen):raise ValueError()
                answers[q['id']]=[o['id'] for o in chosen];break
            except ValueError:output_fn('선택 번호·개수를 확인해주세요. 없음/상관없음은 단독 선택입니다.')
    return {'survey_id':'quick_'+track,'version':VERSION,'answers':answers}

def write_json(path, data):
    """Atomic local replacement; no DB writes or network access."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
            temp=Path(f.name);json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
        os.replace(temp,path)
    finally:
        if temp and temp.exists():temp.unlink()

def main(argv=None):
    parser=argparse.ArgumentParser(description='서버 없이 실행하는 첫 7문항 가중치 계산')
    parser.add_argument('input',nargs='?',help='HTML에서 내려받은 설문응답.json. 생략하면 직접 질문합니다.')
    parser.add_argument('--output',default='results/설문결과.json')
    args=parser.parse_args(argv)
    try:
        if args.input:
            path=Path(args.input)
            if path.resolve()==Path(args.output).resolve():raise ValueError('입력과 출력 파일은 달라야 합니다.')
            if path.stat().st_size>32768:raise ValueError('응답 파일은 32KB 이하여야 합니다.')
            payload=json.loads(path.read_text(encoding='utf-8-sig'))
        else:payload=ask()
        result=evaluate(payload)
        write_json(args.output,result)
        print('\n성향 요약:',result['summary']['title'])
        print('최종 가중치:')
        for feature,score in result['weights'].items():print(f'  {feature}: {score:+g}')
        print('추천 게임:', ', '.join(g['title'] for g in result['recommendation']['games']) or '조건에 맞는 게임 없음')
        print('결과 파일:',Path(args.output).resolve())
        return 0
    except (OSError,ValueError,EOFError) as exc:
        print('실행 오류:',str(exc),file=sys.stderr);return 1
    except KeyboardInterrupt:
        print('\n입력을 취소했습니다.',file=sys.stderr);return 130

if __name__=='__main__':raise SystemExit(main())
