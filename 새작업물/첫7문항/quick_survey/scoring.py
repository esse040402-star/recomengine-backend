"""Server-owned, versioned rules. Internal codes are NOT Steam API IDs."""
import json
import math
from pathlib import Path

VERSION = 'quick-1.0.0'
QUESTIONS = json.loads((Path(__file__).parent / 'data/questions.json').read_text(encoding='utf-8'))
TITLES = ['손맛을 즐기는 도전자','한 수 앞을 보는 전략가','새로운 길을 찾는 탐험가','이야기에 빠지는 감상가','여유를 만드는 힐링 플레이어','승부를 즐기는 챌린저']
# Explicit provisional scoring, to be reviewed by the project team.
PURPOSE = {
 '전투의 손맛': {'genre:action':10},
 '전략과 문제 해결': {'genre:strategy':10,'tag:puzzle':5},
 '이야기에 몰입하기': {'tag:story_rich':10},
 '새로운 발견': {'tag:open_world':10,'genre:adventure':5},
 '휴식과 꾸미기': {'genre:simulation':10,'tag:building':5},
}
SOCIAL = {'solo':'category:single_player','coop':'category:co_op','pvp':'category:pvp'}
VISUAL = {'realistic':'tag:realistic','anime':'tag:anime','pixel':'tag:pixel_graphics','casual':'tag:cute'}
AVOID = {'complex':'preference:complexity','difficulty':'tag:difficult','motion':'preference:motion_intensity','grind':'tag:grindy','monetization':'preference:monetization_pressure','pvp':'category:pvp'}

def definition(track):
    """Only UI rules leave the server, never scoring values."""
    if track not in QUESTIONS:
        raise ValueError('알 수 없는 설문 유형입니다.')
    return {'survey_id':f'quick_{track}', 'version':VERSION, 'track':track,
            'questions':[{'id':q['id'],'field':q['field'],'title':q['title'],'max':q['max'],
            'options':[{'id':o['id'],'label':o['label'],'prefs':{'none':True} if o['prefs'].get('none') else {}} for o in q['options']]} for q in QUESTIONS[track]]}

def validate_answers(track, answers):
    qs = QUESTIONS[track]
    if set(answers) != {q['id'] for q in qs}:
        raise ValueError('q1~q7의 답변을 모두 제출해야 합니다. 추가 질문은 허용되지 않습니다.')
    for q in qs:
        ids = answers[q['id']]
        options = {o['id']:o for o in q['options']}
        if not 1 <= len(ids) <= q['max'] or len(ids) != len(set(ids)) or any(i not in options for i in ids):
            raise ValueError(f"{q['id']}: 선택 개수 또는 선택지 ID가 올바르지 않습니다.")
        if len(ids)>1 and any(options[i]['prefs'].get('none') for i in ids):
            raise ValueError(f"{q['id']}: '상관없음/없음'은 단독으로 선택해주세요.")

def calculate(track, answers):
    validate_answers(track, answers)
    scores, prefs, sums, counts = {}, {'avoid':[], 'platforms':[]}, [0.]*6, [0]*6
    evidence=[]
    def add(code, value):
        scores[code] = scores.get(code,0)+value
    for q in QUESTIONS[track]:
        chosen=[o for o in q['options'] if o['id'] in answers[q['id']]]
        evidence.append({'stage':'quick','field':q['field'],'question':q['title'], 'answer':' · '.join(o['label'] for o in chosen),'axes':[i for i in range(6) if any(o['values'].get(str(i),0)>=65 for o in chosen)]})
        for i in range(6):
            values=[o['values'][str(i)] for o in chosen if str(i) in o['values']]
            if values:
                sums[i]+=sum(values)/len(values); counts[i]+=1
        for o in chosen:
            p=o['prefs']
            for k,v in p.items():
                if k=='none': continue
                if isinstance(v,list): prefs[k]=list(dict.fromkeys(prefs.get(k,[])+v))
                else: prefs[k]=v
            for code,value in PURPOSE.get(p.get('purpose'),{}).items(): add(code,value)
            if p.get('social') in SOCIAL: add(SOCIAL[p['social']],10)
            if p.get('visual') in VISUAL: add(VISUAL[p['visual']],5)
            for avoid in p.get('avoid',[]): add(AVOID[avoid],-10)
            if p.get('lowSpec'): add('hardware:low_spec',10)
            if p.get('session'): add('session:'+p['session'],5)
            if q['field']=='mechanics':
                rules=({'0':{'tag:action':5},'1':{'tag:turn_based':5}} if track=='gamer' else {'0':{'preference:free_movement':5},'1':{'tag:point_and_click':5}})
                for code,value in rules.get(o['id'],{}).items(): add(code,value)
    axes=[math.floor(sums[i]/counts[i]+.5) if counts[i] else 50 for i in range(6)]
    top=sorted(range(6),key=lambda i:-axes[i])[:2]
    summary={'axes':axes,'coverage':[c>0 for c in counts],'top':top,'title':TITLES[top[0]],'prefs':prefs,'evidence':evidence,'stage':'quick','count':7}
    return {'weights':dict(sorted(scores.items())), 'summary':summary,
            'constraints':{'platforms':prefs['platforms'],'avoid':prefs['avoid'],'budget':None,'hardware_spec':None,'low_spec_preferred':bool(prefs.get('lowSpec'))},
            'recommendation':{'status':'awaiting_steam_adapter','games':[]}, 'rules_version':VERSION}
