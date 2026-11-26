import React from 'react';
export function deepIntro(ctx) {
  return <div className="panel intro-panel"><div className="big-icon">{ctx.icon('Sparkles')}</div><h1>{'질문지를 넘어,'}<br /><span className="gradient-text">{'AI와 직접 대화해보세요.'}</span></h1><p>{'기존 28문항 맞춤 설문은 자유 대화형 AI 추천으로 대체되었어요.'}<br />{'원하는 게임을 편하게 설명하면 AI가 필요한 내용을 물어보고 게임 5개를 추천합니다.'}</p><div className="intro-points"><div className="intro-point"><b>{ctx.icon('MessageCircle')}</b>{'자유 대화'}</div><div className="intro-point"><b>{ctx.icon('Sparkles')}</b>{'자동 추천'}</div><div className="intro-point"><b>5</b>{'맞춤 게임'}</div></div><div className="row">{ctx.routeBtn(<>{'AI 추천 시작하기'}{ctx.icon('ArrowRight')}</>, 'home', 'btn primary')}{ctx.routeBtn('나중에', 'home', 'btn ghost')}</div></div>;
}
