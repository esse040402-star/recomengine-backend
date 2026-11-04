import E from './preferenceEngine';
import { request, apiEnabled } from './transport';
export async function generateSurvey(session, requestText = '', { includeProfileContext = true, signal } = {}) {
  const seed = E.seedAnswers(session), questions = E.deepQuestions(session.track, seed);
  if (!apiEnabled) return { questions, source: 'adaptive' };
  try {
    const payload = await request('/api/survey/generate', {
      method: 'POST', timeout: 55000, signal, body: {
        track: session.track, answers: seed, request: requestText.trim().slice(0, 300),
        blueprint: E.publicBlueprint(session.track, seed),
        ...(includeProfileContext ? { profileContext: { axes: E.report(session).axes, prefs: E.report(session).prefs } } : {}),
      }
    });
    return { questions: E.applyAI(questions, payload), source: payload.source === 'ollama' ? 'ollama' : 'ai' };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { questions, source: 'adaptive' };
  }
}
export async function saveDiagnosisToBackend(state) {
  if (!apiEnabled || !state.track) return null;

  const report = E.report(state);

  // 1. 진단 세션 생성 (비회원도 가능)
  const session = await request('/api/sessions', {
    method: 'POST',
    body: { track: state.track },
  });

  // 2. 완료된 설문 답변 모으기
  const answerMap = new Map();

  for (const kind of ['quick', 'deep', 'preference']) {
    const survey = state[kind];

    if (!survey?.completed || !survey.answers) continue;

    for (const [question_id, answer] of Object.entries(survey.answers)) {
      if (answer !== null && answer !== undefined) {
        answerMap.set(question_id, { question_id, answer });
      }
    }
  }

  const answers = [...answerMap.values()];

  if (answers.length > 0) {
    await request(`/api/sessions/${session.id}/answers`, {
      method: 'PUT',
      body: { answers },
    });
  }

  // 3. 분석 결과와 추천 게임 저장
  return request(`/api/sessions/${session.id}/complete`, {
    method: 'POST',
    body: {
      axes: report.axes,
      title: report.title || null,
      prefs: report.prefs || {},
      evidence: report.evidence || [],
    },
  });
}
