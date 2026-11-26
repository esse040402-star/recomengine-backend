// TODO: FastAPI / Supabase 저장 요청을 여기에 연결함. 현재는 reducer → storage에 보관함.
export function toggleFeedback(previous={},value){const next={...previous,updatedAt:new Date().toISOString()};if(value==='played'||value==='hidden')next[value]=!next[value];else next.sentiment=next.sentiment===value?null:value;return next;}
