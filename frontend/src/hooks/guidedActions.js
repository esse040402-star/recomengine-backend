import E from '../services/preferenceEngine';
import {initialState} from '../state/appReducer';
import {generateSurvey} from '../services/recommendationService';
import {chooseOption} from './surveyActions';
export function guidedActions(c){const set=guidedChat=>c.setUI({guidedChat});const generate=async chat=>{set({...chat,stage:'generating'});const token=++c.requestEpoch.current;const generated=await generateSurvey(chat.session,chat.request);if(token!==c.requestEpoch.current)return;set({...chat,questions:generated.questions,source:generated.source,stage:'deep',index:0,answers:{}});};return {
 'guided-mode':({value})=>{const chat={mode:value,stage:value==='fresh'||!c.state.quick?.completed?'track':'generating',session:structuredClone(value==='fresh'?initialState:c.state),index:0,answers:{},request:c.fields.current['recommendation-input']?.value||''};if(chat.stage==='generating')generate(chat);else set(chat);},
 'guided-track':({value})=>set({...c.guidedChat,session:{...c.guidedChat.session,track:value},stage:'quick',index:0,answers:{}}),
 'guided-answer':({value})=>{const chat=c.guidedChat,qs=chat.stage==='quick'?E.quickQuestions(chat.session.track):chat.questions;set({...chat,answers:chooseOption(qs[chat.index],chat.answers,value)});},
 'guided-next':()=>{const chat=c.guidedChat,qs=chat.stage==='quick'?E.quickQuestions(chat.session.track):chat.questions;if(!chat.answers[qs[chat.index].id]?.length)return;if(chat.index<qs.length-1){set({...chat,index:chat.index+1});return;}if(!E.validAnswers(qs,chat.answers))return;const result={completed:true,questions:qs,answers:chat.answers,source:chat.source,completedAt:new Date().toISOString()};if(chat.stage==='quick'){const next={...chat,session:{...chat.session,quick:{...result,schema:2}}};generate(next);}else set({...chat,session:{...chat.session,deep:result},stage:'result'});},
 'guided-prev':()=>set({...c.guidedChat,index:Math.max(0,c.guidedChat.index-1)}),
 'guided-reset':()=>{c.requestEpoch.current++;set(null)},
 'guided-pause':()=>set({...c.guidedChat,paused:true}), 'guided-resume':()=>set({...c.guidedChat,paused:false}),
 'guided-save':()=>c.showDialog('guided-save'),
 'guided-confirm-save':()=>{const chat=c.guidedChat;if(chat?.stage!=='result')return;const drafts={...c.state.drafts};delete drafts.deep;c.patch({track:chat.session.track,quick:chat.session.quick,deep:chat.session.deep,drafts,...(chat.mode==='fresh'?{filters:{}}:{})});c.closeDialog();c.toast('이번 답변을 추천 기준에 반영했어요.');}
 };}
