import { chatRecommend } from '../services/recommendationService';

export function guidedActions(c) {
  return {
    'chat-reset': () => { c.requestEpoch.current++; c.setUI({ chatTurns: [], chatBusy: false }); },
    'chat-mode-profile': () => { c.requestEpoch.current++; c.setUI({ chatMode: 'profile', chatTurns: [], chatBusy: false }); },
    'chat-mode-conversation': () => { c.requestEpoch.current++; c.setUI({ chatMode: 'conversation', chatTurns: [], chatBusy: false }); },
    'chat-send': async ({ value } = {}) => {
      const message = String(value || c.fields.current['recommendation-input']?.value || '').trim();
      if (!message || c.chatBusy) return;
      const previous = c.chatTurns || [];
      const history = previous.flatMap(turn => [
        { role: 'user', content: turn.user },
        ...(turn.reply ? [{ role: 'assistant', content: turn.reply }] : []),
      ]).slice(-20);
      const token = ++c.requestEpoch.current;
      const pending = [...previous, { user: message, pending: true }];
      c.setUI({ chatTurns: pending, chatBusy: true });
      if (c.fields.current['recommendation-input']) c.fields.current['recommendation-input'].value = '';
      try {
        const report = c.E.report(c.state);
        const mode = c.chatMode || 'conversation';
        const hasProfile = !!(c.state.preference?.completed || c.state.quick?.completed);
        if (mode === 'profile' && !hasProfile) throw new Error('성향 프로필 기반 추천을 사용하려면 먼저 빠른 취향 찾기 또는 플레이 성향 프로필을 완료해 주세요.');
        const profileContext = mode === 'profile' && hasProfile
          ? { title: report.title, axes: report.axes, prefs: report.prefs }
          : null;
        const result = await chatRecommend(message, history, profileContext, { mode });
        if (token !== c.requestEpoch.current) return;
        c.setUI({ chatTurns: [...pending.slice(0, -1), { user: message, reply: result.reply, results: result.results || [], ready: result.ready }], chatBusy: false });
      } catch (error) {
        if (token !== c.requestEpoch.current) return;
        c.setUI({ chatTurns: [...previous, { user: message, reply: error.message || 'AI 추천 요청에 실패했어요. 잠시 후 다시 시도해주세요.', error: true }], chatBusy: false });
      }
    },
  };
}
