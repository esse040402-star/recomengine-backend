import {initialState} from '../state/appReducer';
import E from '../services/preferenceEngine';
export const STORAGE_KEY='recom-integrated-v3';
export function normalizeState(value){const s={...structuredClone(initialState),...value,profile:{...initialState.profile,...value?.profile},home:{...initialState.home,...value?.home},drafts:value?.drafts||{}};if(s.quick?.completed&&!s.quick.questions)s.quick.questions=E.legacyQuickQuestions(s.track);for(const p of [s.preference,s.drafts.preference])if(p&&s.track){p.track=p.track||s.track;p.questions=p.questions||E.profileQuestions(p.track);}if(s.drafts.quick&&!s.drafts.quick.schema)delete s.drafts.quick;return s;}
export function readState(){try{return normalizeState(JSON.parse(localStorage.getItem(STORAGE_KEY)||'null'));}catch{return structuredClone(initialState);}}
export function writeState(state,key=STORAGE_KEY){try{localStorage.setItem(key,JSON.stringify(state));return true;}catch{return false;}}
