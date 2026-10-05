import {toggleFeedback} from '../services/feedbackService';
import * as account from '../services/accountService';
import {normalizeState} from '../utils/storage';
export function profileActions(c){const form=id=>c.forms.current[id],valid=id=>form(id)?.reportValidity(),data=id=>new FormData(form(id));return {
 'mode':({value})=>c.patch({mode:value}), 'dismiss-banner':()=>c.patch({bannerDismissed:true}),
 'save':({id})=>{c.dispatch({type:'save-game',id});c.toast(c.state.saved.includes(id)?'찜한 게임에서 뺐어요.':'찜한 게임에 담았어요.');},
 'game-feedback':({id})=>c.showDialog('feedbackDialog',{id}),
 'feedback-choice':({id,value})=>{c.dispatch({type:'feedback',id,feedback:toggleFeedback(c.state.feedback[id],value)});c.toast('취향 피드백을 추천에 반영했어요.');},
 'feedback-clear':({id})=>{const feedback={...c.state.feedback};delete feedback[id];c.patch({feedback});c.closeDialog();},
 'filters':()=>c.showDialog('filtersDialog'),
 'apply-filters':()=>{const f=data('filter-form');c.patch({filters:{platforms:f.getAll('platforms'),avoid:f.getAll('avoid')}});c.closeDialog();},
 'reset-filters':()=>{c.patch({filters:{}});c.closeDialog();},
 'customize':()=>c.showDialog('customizeBody',{},c.state.home),
 'home-style':({value})=>c.setUI({dialogDraft:{...c.dialogDraft,style:value}}),
 'home-game':({id})=>c.setUI({dialogDraft:{...c.dialogDraft,game:id}}),
 'save-home':()=>{c.patch({home:c.dialogDraft});c.closeDialog();c.toast('홈 색상을 적용했어요.');},
 'apply-theme':({id})=>{c.patch({home:{style:'fixed',game:id}});c.goto('home');c.toast('이 게임의 색상을 홈에 적용했어요.');},
 'edit-profile':()=>c.showDialog('profileEditorBody',{},c.state.profile),
 'avatar':({value})=>c.setUI({dialogDraft:{...c.dialogDraft,avatar:value}}),
 'profile-color':({value})=>c.setUI({dialogDraft:{...c.dialogDraft,color:value}}),
 'profile-banner':({id})=>c.setUI({dialogDraft:{...c.dialogDraft,banner:id}}),
 'save-profile':()=>{if(!valid('profile-form'))return;const f=data('profile-form'),name=String(f.get('name')).trim();if(!name)return;c.patch({profile:{...c.dialogDraft,name,bio:String(f.get('bio')).trim()}});c.closeDialog();c.toast('프로필을 저장했어요.');},
 'write-review':({id})=>{c.setUI({reviewGame:id});c.showDialog('reviewForm',{id});},
 'save-review':()=>{if(!valid('review-form'))return;const f=data('review-form'),text=String(f.get('text')).trim();if(text.length<10)return c.toast('플레이 경험을 10자 이상 입력해주세요.');const id=f.get('game');c.patch({reviews:[{id:crypto.randomUUID(),game:id,rating:Number(f.get('rating')),text,name:c.state.profile.name},...c.state.reviews]});c.goto('game/'+id+'/reviews');c.toast('내 평가를 저장했어요.');},
 'restart-onboarding':()=>c.showDialog('restartDialog'),
 'account-login':()=>c.showDialog('accountDialog',{signup:false}),
 'account-signup':()=>c.showDialog('accountDialog',{signup:true}),
 'account-submit':async()=>{if(!valid('account-form'))return;try{const result=await account[c.dialog.params.signup?'signup':'login'](Object.fromEntries(data('account-form')));c.setUI({accountUser:result.user});c.dispatch({type:'replace',state:normalizeState(result.state||c.state)});c.goto('home');}catch(e){c.toast(e.message)}},
 'account-logout':async()=>{try{await account.saveAccountState(c.state);await account.logout();c.setUI({accountUser:null});c.dispatch({type:'replace',state:normalizeState(null)});c.goto('welcome');}catch(e){c.toast(e.message)}}
 };}
