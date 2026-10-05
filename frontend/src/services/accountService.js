import {request} from './transport';
// TODO: FastAPI / Supabase Auth adapter. 브라우저에 비밀번호를 저장하지 않음.
export const login=data=>request('/api/account/login',{method:'POST',body:data});
export const signup=data=>request('/api/account/signup',{method:'POST',body:data});
export const session=()=>request('/api/account/session');
export const logout=()=>request('/api/account/logout',{method:'POST'});
export const saveAccountState=state=>request('/api/account/state',{method:'PUT',body:{state}});
