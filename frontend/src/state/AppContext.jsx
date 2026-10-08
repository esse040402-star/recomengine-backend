import {createContext,useContext,useEffect,useMemo,useReducer,useRef,useState} from 'react';
import {appReducer} from './appReducer';
import {readState,writeState,normalizeState,STORAGE_KEY} from '../utils/storage';
import E from '../services/preferenceEngine';
import * as account from '../services/accountService';
import {apiEnabled} from '../services/transport';
import {createStateSaveQueue} from '../services/stateSaveQueue';
const AppContext=createContext(null);
const pendingKey=user=>`${STORAGE_KEY}:pending:${user.id}`;
function pendingState(user){try{return JSON.parse(localStorage.getItem(pendingKey(user))||'null');}catch{return null;}}

export function AppProvider({children}) {
  const [state,dispatch]=useReducer(appReducer,undefined,readState);
  const [storageError,setStorageError]=useState(false);
  const [auth,setAuth]=useState({user:null,ready:!apiEnabled,busy:false,status:'guest',error:''});
  const latest=useRef(state), queue=useRef(null), timer=useRef(null), accepted=useRef(null), busy=useRef(false);
  latest.current=state;
  const connect=(user, next, mustSave=false)=>{
    clearTimeout(timer.current); queue.current?.close();
    accepted.current=JSON.stringify(next);
    const recovery=pendingState(user);
    queue.current=createStateSaveQueue(async value=>{
      await account.saveAccountState(value);
      // 더 최신 변경이 대기 중이면 그 복구본은 지우지 않습니다.
      try{if(JSON.stringify(pendingState(user))===JSON.stringify(value))localStorage.removeItem(pendingKey(user));}catch{ /* 저장 공간 접근 실패는 기존 경고로 안내 */ }
    },(status,error)=>{
      setAuth(a=>({...a,status,error:error?.message||''}));
    });
    dispatch({type:'replace',state:next});
    setAuth({user,ready:true,busy:false,status:mustSave?'saving':'saved',error:'',recovery});
    if(mustSave){writeState(next,pendingKey(user));queue.current.enqueue(next);void queue.current.flush().catch(()=>{});}
  };
  useEffect(()=>{
    if(!apiEnabled)return;
    const controller=new AbortController();
    account.session({signal:controller.signal}).then(result=>{
      if(controller.signal.aborted)return;
      if(result?.user)connect(result.user,normalizeState(result.state || {profile:{name:result.user.name}}));
      else setAuth(a=>({...a,ready:true}));
    }).catch(error=>{
      if(!controller.signal.aborted)setAuth(a=>({...a,ready:true,error:error.message,status:'offline'}));
    });
    return ()=>{controller.abort();clearTimeout(timer.current);queue.current?.close();};
  },[]);
  useEffect(()=>{
    if(!auth.ready)return;
    // 회원의 저장 자료를 게스트 저장 영역에 섞지 않습니다.
    const key=auth.user?`${STORAGE_KEY}:account:${auth.user.id}`:STORAGE_KEY;
    setStorageError(!writeState(state,key));
    const serialized=JSON.stringify(state);
    if(auth.user&&serialized!==accepted.current){
      accepted.current=serialized;if(!writeState(state,pendingKey(auth.user)))setStorageError(true);queue.current.enqueue(state);setAuth(a=>({...a,status:'pending'}));
      clearTimeout(timer.current);timer.current=setTimeout(()=>void queue.current.flush().catch(()=>{}),700);
    }
  },[state,auth.ready,auth.user]);
  useEffect(()=>{
    const guard=e=>{if(auth.user&&queue.current?.dirty){e.preventDefault();e.returnValue='';}};
    window.addEventListener('beforeunload',guard);
    return ()=>window.removeEventListener('beforeunload',guard);
  },[auth.user]);
  const authenticate=async(signup, form)=>{
    if(busy.current)return false;
    busy.current=true;setAuth(a=>({...a,busy:true,error:''}));
    const guest=structuredClone(latest.current);
    try {
      const result=await account[signup?'signup':'login'](form);
      if(!result?.user?.id)throw Error('계정 응답을 확인할 수 없습니다.');
      const next=normalizeState(result.state || (signup?{...guest,profile:{...guest.profile,name:result.user.name}}:{profile:{name:result.user.name}}));
      connect(result.user,next,signup&&!result.state);
      return true;
    } catch(error){setAuth(a=>({...a,error:error.message}));throw error;}
    finally{busy.current=false;setAuth(a=>({...a,busy:false}));}
  };
  const logout=async()=>{
    if(busy.current)return false;
    busy.current=true;setAuth(a=>({...a,busy:true}));
    try{
      clearTimeout(timer.current);
      // 클릭 직후의 마지막 변경까지 저장한 뒤 세션을 종료합니다. 실패하면 로그인을 유지합니다.
      queue.current?.enqueue(latest.current);await queue.current?.flush();await account.logout();
      queue.current?.close();queue.current=null;accepted.current=null;
      dispatch({type:'replace',state:readState()});
      setAuth({user:null,ready:true,busy:false,status:'guest',error:''});return true;
    }finally{busy.current=false;setAuth(a=>({...a,busy:false}));}
  };
  const recoverLocal=()=>{if(auth.recovery){dispatch({type:'replace',state:normalizeState(auth.recovery)});setAuth(a=>({...a,recovery:null}));}};
  const retrySave=()=>{clearTimeout(timer.current);return queue.current?.flush() || Promise.resolve();};
  const analysis=useMemo(()=>E.report(state),[state]);
  return <AppContext.Provider value={{state,dispatch,analysis,storageError,auth,authenticate,logout,retrySave,recoverLocal}}>{children}</AppContext.Provider>;
}
export const useApp=()=>useContext(AppContext);
