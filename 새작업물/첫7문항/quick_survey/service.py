"""Pure entry point for future frontend/DB/API integration; no I/O or server."""
from .scoring import VERSION, calculate, QUESTIONS

def evaluate(payload: dict) -> dict:
    if not isinstance(payload,dict) or set(payload)!={'survey_id','version','answers'}:
        raise ValueError('survey_id, version, answers만 입력해주세요.')
    track={'quick_gamer':'gamer','quick_nongamer':'nongamer'}.get(payload.get('survey_id')) if isinstance(payload.get('survey_id'),str) else None
    if track is None: raise ValueError('설문 ID가 올바르지 않습니다.')
    if payload['version']!=VERSION: raise ValueError('설문 버전이 일치하지 않습니다.')
    answers=payload['answers']
    if not isinstance(answers,dict) or len(answers)!=7:
        raise ValueError('7문항 답변 객체가 필요합니다.')
    for key,values in answers.items():
        if not isinstance(key,str) or not isinstance(values,list) or not all(isinstance(v,str) for v in values):
            raise ValueError('답변은 질문 ID별 선택지 ID 문자열 배열이어야 합니다.')
    result=calculate(track,answers)
    from .steam import recommend
    result["recommendation"]=recommend(result["weights"],result["constraints"])
    return {'survey_id':payload['survey_id'],'version':VERSION,'answers':{k:list(v) for k,v in answers.items()},**result}
