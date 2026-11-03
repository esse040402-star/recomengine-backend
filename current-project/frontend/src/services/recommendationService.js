import E from './preferenceEngine';
import {request, apiEnabled} from './transport';
export async function generateSurvey(session, requestText='', {includeProfileContext=true, signal}={}) {
  const seed = E.seedAnswers(session), questions = E.deepQuestions(session.track, seed);
  if (!apiEnabled) return {questions,source:'adaptive'};
  try {
    const payload = await request('/api/survey/generate', {method:'POST',timeout:55000,signal,body:{
      track:session.track, answers:seed, request:requestText.trim().slice(0,300),
      blueprint:E.publicBlueprint(session.track,seed),
      ...(includeProfileContext ? {profileContext:{axes:E.report(session).axes,prefs:E.report(session).prefs}} : {}),
    }});
    return {questions:E.applyAI(questions,payload), source:payload.source === 'ollama' ? 'ollama' : 'ai'};
  } catch (error) {
    if (signal?.aborted) throw error;
    return {questions,source:'adaptive'};
  }
}
