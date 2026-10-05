import E from './preferenceEngine';
import {request} from './transport';
export async function generateSurvey(session,requestText=''){const seed=E.seedAnswers(session),questions=E.deepQuestions(session.track,seed);if(!import.meta.env.VITE_API_BASE_URL)return {questions,source:'adaptive'};try{const payload=await request('/api/survey/generate',{method:'POST',body:{track:session.track,answers:seed,request:requestText,profileContext:{axes:E.report(session).axes,prefs:E.report(session).prefs}}});return {questions:E.applyAI(questions,payload),source:'openai'};}catch{return {questions,source:'adaptive'};}}
// TODO: FastAPI → Ollama 연결 시 생성 문항 검증과 기존 옵션 점수 유지.
