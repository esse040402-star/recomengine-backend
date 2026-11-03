import test from 'node:test';
import assert from 'node:assert/strict';
import {request,ApiError} from '../src/services/transport.js';
import {createStateSaveQueue} from '../src/services/stateSaveQueue.js';
import {resolveRoute} from '../src/utils/routes.js';

test('204 응답과 쿠키 전송',async()=>{
 const old=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{assert.equal(url,'/api/account/logout');assert.equal(options.credentials,'include');assert.equal(options.headers['Content-Type'],undefined);return new Response(null,{status:204});};
 try{assert.equal(await request('/api/account/logout',{method:'POST'}),null);}finally{globalThis.fetch=old;}
});
test('신규 명세 오류와 기존 서버 오류를 모두 처리',async()=>{
 const old=globalThis.fetch;
 try{for(const body of [{message:'충돌',code:'STATE_CONFLICT',details:[{field:'version'}]},{error:'충돌'}]){
  globalThis.fetch=async()=>new Response(JSON.stringify(body),{status:409});
  await assert.rejects(()=>request('/api/test'),e=>e instanceof ApiError&&e.status===409&&e.message==='충돌');
 }}finally{globalThis.fetch=old;}
});
test('JSON 대신 HTML이 반환되면 성공으로 처리하지 않음',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response('<html>vite</html>');
 try{await assert.rejects(()=>request('/api/test'),e=>e.code==='INVALID_RESPONSE');}finally{globalThis.fetch=old;}
});
test('POST 원문을 JSON으로 전달',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async(_,options)=>{assert.deepEqual(JSON.parse(options.body),{state:{version:3}});return new Response('{"ok":true}');};
 try{assert.deepEqual(await request('/api/account/state',{method:'PUT',body:{state:{version:3}}}),{ok:true});}finally{globalThis.fetch=old;}
});
test('연속 변경은 직렬 저장하고 마지막 상태 보장',async()=>{
 const calls=[];let unblock;
 const queue=createStateSaveQueue(async v=>{calls.push(v.n);if(v.n===1)await new Promise(r=>{unblock=r;});});
 queue.enqueue({n:1});const wait=queue.flush();queue.enqueue({n:2});queue.enqueue({n:3});unblock();await wait;
 assert.deepEqual(calls,[1,3]);assert.equal(queue.dirty,false);
});
test('실패한 저장은 보관하고 명시적 재시도',async()=>{
 let fail=true;const saved=[];const q=createStateSaveQueue(async v=>{if(fail)throw Error('offline');saved.push(v);});
 q.enqueue({n:1});await assert.rejects(()=>q.flush());assert.equal(q.dirty,true);
 fail=false;await q.flush();assert.deepEqual(saved,[{n:1}]);assert.equal(q.dirty,false);
});
test('온보딩 보호·잘못된 경로·리뷰 별칭',()=>{
 const guest={state:{drafts:{}},user:null,gameExists:id=>id==='elden',firstGame:'elden'};
 assert.equal(resolveRoute('profile',guest),'welcome');assert.equal(resolveRoute('survey/quick',guest),'welcome');
 const member={...guest,user:{id:'1'}};
 assert.equal(resolveRoute('welcome',member),'home');assert.equal(resolveRoute('welcome',{...member,forceOnboarding:true}),'welcome');
 assert.equal(resolveRoute('reviews',member),'game/elden/reviews');assert.equal(resolveRoute('game/missing',member),'home');assert.equal(resolveRoute('unknown',member),'home');
});

test('설문 완료 직후 초안 제거와 화면 이동 사이에도 결과 화면 유지',()=>{
 const data={state:{drafts:{},quick:{completed:true}},user:null,gameExists:()=>true};
 assert.equal(resolveRoute('survey/quick',data),'result');
 assert.equal(resolveRoute('survey/preference',{...data,state:{...data.state,preference:{completed:true}}}),'report');
});
