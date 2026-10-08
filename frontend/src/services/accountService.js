import {request} from './transport';
// 업로드된 FastAPI 서버에 실제 존재하는 경로입니다. v1 명세는 docs/DB연결_변경내역.md 참고.
export const login = ({email, password}) => request('/api/account/login', {method:'POST',body:{email:email.trim(),password}});
export const signup = ({name, email, password}) => request('/api/account/signup', {method:'POST',body:{name:name.trim(),email:email.trim(),password}});
export const session = options => request('/api/account/session', options);
export const logout = () => request('/api/account/logout', {method:'POST'});
export const saveAccountState = state => request('/api/account/state', {method:'PUT',body:{state}});
