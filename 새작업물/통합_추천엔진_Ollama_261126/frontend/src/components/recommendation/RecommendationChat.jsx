import React from 'react';
import { ActionButton, GameImage, Field, Form } from '../../components/common/Elements.jsx';

export function recommendationChat(ctx) {
  const greeting = ctx.chatGreetings[0];
  const turns = ctx.chatTurns || [];
  const mode = ctx.chatMode || 'conversation';
  const hasProfile = !!(ctx.state.preference?.completed || ctx.state.quick?.completed);
  return (
    <section className="recommend-chat" aria-labelledby="chat-heading">
      <div className="chat-heading">
        <span className="chat-mark">{ctx.icon('Sparkles')}</span>
        <h1 id="chat-heading"><>{ctx.esc(greeting[0])}{' '}</><span className="gradient-text">{ctx.esc(greeting[1])}</span></h1>
        <p>원하는 게임을 편하게 설명해주세요. 대화를 통해 취향을 파악하고 게임 5개를 추천해드려요.</p>
      </div>
      <div className="chat-mode-panel" aria-label="AI 추천 방식 선택">
        <p className="chat-mode-title">어떤 방식으로 추천받을까요?</p>
        <div className="chat-mode-options">
          <ActionButton className={`chat-mode-option${mode === 'profile' ? ' active' : ''}${!hasProfile ? ' unavailable' : ''}`} data-action="chat-mode-profile" aria-pressed={mode === 'profile'} aria-disabled={!hasProfile}>
            <strong>성향 프로필 기반 AI 추천</strong>
            <small>설문으로 분석한 취향과 대화 내용을 함께 반영</small>
            {!hasProfile && <small>사용하려면 먼저 취향 설문을 완료하세요</small>}
          </ActionButton>
          <ActionButton className={`chat-mode-option${mode === 'conversation' ? ' active' : ''}`} data-action="chat-mode-conversation" aria-pressed={mode === 'conversation'}>
            <strong>프로필 없이 대화 기반 AI 추천</strong>
            <small>저장된 프로필 없이 지금 대화에서 취향을 새롭게 파악</small>
          </ActionButton>
        </div>
        {!hasProfile && <p className="chat-mode-note">성향 프로필을 먼저 만들고 싶다면 {ctx.routeBtn('취향 프로필 만들기', 'survey/quick', 'text-btn')}를 진행하세요.</p>}
        {turns.length > 0 && <ActionButton className="text-btn chat-new" data-action="chat-reset">새 대화</ActionButton>}
      </div>
      <div className="recommendation-thread" aria-live="polite">
        {turns.map((turn, index) => (
          <div className="chat-turn" key={`${index}-${turn.user}`}>
            <div className="chat-user">{turn.user}</div>
            {turn.reply && <div className={`chat-answer${turn.error ? ' chat-error' : ''}`}><p>{turn.reply}</p></div>}
            {turn.pending && <div className="chat-answer"><p><span className="spinner" /> 답변을 분석하고 있어요.</p></div>}
            {turn.results?.length > 0 && (
              <div className="chat-answer">
                <p><strong>추천 게임 {turn.results.length}개</strong></p>
                <div className="chat-results">
                  {turn.results.map((item, i) => {
                    const game = item.game || {};
                    return (
                      <button className="chat-result" type="button" key={game.id || game.title || i} onClick={() => game.id && ctx.goto(`game/${game.id}`)}>
                        <GameImage src={game.cover_url || '/assets/image-fallback.svg'} alt={`${game.title || '게임'} 표지`} />
                        <span><strong>{game.title}</strong><small>{item.reason || (game.genres || []).slice(0, 2).join(' · ')}</small></span>
                        {ctx.icon('ChevronRight')}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {turn.ready && turn.results?.length === 0 && <div className="chat-answer"><p>조건에 맞는 게임을 충분히 찾지 못했어요. 기기나 선호 조건을 조금 바꿔서 다시 이야기해 주세요.</p></div>}
          </div>
        ))}
        {ctx.chatBusy && turns.length === 0 && <div className="chat-answer"><p><span className="spinner" /> AI와 연결하고 있어요.</p></div>}
      </div>
      <Form className="chat-composer" id="recommendation-form">
        <label className="sr-only" htmlFor="recommendation-input">원하는 게임 조건</label>
        <Field id="recommendation-input" maxLength={500} autoComplete="off" disabled={ctx.chatBusy} placeholder="예: 혼자 할 수 있고 스토리가 좋은 PC 게임을 찾고 있어요" />
        <ActionButton type="submit" className="chat-send" aria-label="메시지 보내기" disabled={ctx.chatBusy}>{ctx.icon('ArrowRight')}</ActionButton>
      </Form>
      <div className="chat-suggestions"><span className="chat-method">{mode === 'profile' ? '저장된 성향 프로필과 이번 대화가 함께 반영됩니다.' : '저장된 성향 프로필은 사용하지 않고 이번 대화 내용만 반영됩니다.'}</span></div>
    </section>
  );
}
