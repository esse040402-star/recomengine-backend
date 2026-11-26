import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';

const here=dirname(fileURLToPath(import.meta.url));
const root=resolve(here,'..');
const source=readFileSync(resolve(root,'src/services/preferenceEngine.js'),'utf8')
  .replace(/^import PROFILE .*;\s*$/m,'')
  .replace(/^import CATALOG .*;\s*$/m,'')
  .replace('export default {legacyQuickQuestions,seedAnswers,AXES,RISK_LABELS,PLATFORM_LABELS,quickQuestions,profileQuestions,deepQuestions,quickContext,validAnswers,report,recommend,explainGame,sections,publicBlueprint,applyAI};',
    'globalThis.__engine={profileQuestions,quickQuestions,report,recommend};');
const PROFILE=JSON.parse(readFileSync(resolve(root,'src/data/generated/profileSource.json'),'utf8'));
const CATALOG=JSON.parse(readFileSync(resolve(root,'src/data/generated/catalog.json'),'utf8'));
const sandbox={PROFILE,CATALOG,console};
runInNewContext(source,sandbox);
const engine=sandbox.__engine;
const neutral=/상관없|잘 모르겠|특별히 선호|특별히 싫어|특별히 피하고|상황에 따라|게임에 따라 다름|경쟁 방식에 따라|일정하지 않|일정한 시간 없이|관심 없음|관심이 없음|경험이 적어|불편하지 않|불편한 화면 연출 없음|떠오르는 이유는 없|아직 정하지|아직 잘 모르|관계없이 혼자 만족/i;

function oneAnswer(track,questions,q,o){
  return engine.report({track,preference:{completed:true,track,questions,answers:{[q.id]:[o.id]}}});
}

test('게이머·비게이머 프로필 366개 선택지가 모두 결과 근거로 전달된다',()=>{
  let count=0;
  for(const track of ['gamer','nongamer']){
    const quick=engine.quickQuestions(track);
    for(const q of quick)for(const o of q.options){
      const result=oneAnswer(track,quick,q,o);
      assert.equal(result.count,1,`${track} ${q.id}: ${o.label} 선택 수`);
      assert.ok(result.evidence.some(e=>e.answer===o.label),`${track} ${q.id}: ${o.label} 근거 누락`);
      assert.ok(Array.isArray(result.recommendations));
      count++;
    }
    const questions=engine.profileQuestions(track);
    for(const q of questions)for(const o of q.options){
      const result=oneAnswer(track,questions,q,o);
      assert.equal(result.count,1,`${track} ${q.id}: ${o.label} 선택 수`);
      assert.ok(result.evidence.some(e=>e.answer===o.label),`${track} ${q.id}: ${o.label} 근거 누락`);
      assert.ok(Array.isArray(result.recommendations),`${track} ${q.id}: ${o.label} 추천 결과 없음`);
      const hasScore=Object.values(o.values||{}).some(v=>Number.isFinite(v)&&v!==50);
      const preferenceKeys=Object.keys(o.prefs||{}).filter(k=>k!=='none'&&!(k==='platforms'&&!o.prefs.platforms.length));
      if(hasScore)assert.notDeepEqual(Array.from(result.axes),[50,50,50,50,50,50],`${track} ${q.id}: ${o.label} 점수 미반영`);
      else if(preferenceKeys.length)for(const key of preferenceKeys)assert.ok(Object.hasOwn(result.prefs,key),`${track} ${q.id}: ${o.label} ${key} 미반영`);
      else assert.ok(neutral.test(o.label)||Object.values(o.values||{}).length>0,`${track} ${q.id}: ${o.label} 점수·메타데이터 없는 비중립 선택지`);
      count++;
    }
  }
  assert.equal(count,366);
});

test('의미가 있는 무점수 선택지는 축 점수 또는 구조화 선호 정보로 보존된다',()=>{
  const expected=[
    ['gamer','p10',4,'skill_expression'],
    ['gamer','p7',4,'purpose'],
    ['gamer','p11',4,'team_role'],
    ['gamer','p14',4,'purpose'],
    ['gamer','p24',3,'skill_expression'],
    ['gamer','p27',3,'social'],
    ['gamer','p30',4,'purpose'],
    ['nongamer','p4',3,'automation'],
    ['nongamer','p11',3,'pace'],
    ['nongamer','p13',4,'purpose'],
    ['nongamer','p15',3,'control'],
    ['nongamer','p24',3,'learning'],
    ['nongamer','p26',3,'purpose']
  ];
  for(const [track,qid,index,key] of expected){
    const questions=engine.profileQuestions(track),q=questions.find(x=>x.id===qid),o=q.options[index];
    const result=oneAnswer(track,questions,q,o);
    assert.ok(Object.hasOwn(result.prefs,key),`${track} ${qid} ${o.label}: ${key} 누락`);
    assert.ok(result.evidence.some(e=>e.answer===o.label));
  }
});

test('중립·불확실 응답은 임의 취향 점수를 만들지 않는다',()=>{
  for(const track of ['gamer','nongamer']){
    const questions=engine.profileQuestions(track);
    for(const q of questions)for(const o of q.options){
      const hasSignal=Object.values(o.values||{}).some(v=>Number.isFinite(v)) || Object.keys(o.prefs||{}).length>0;
      if(!hasSignal && neutral.test(o.label)){
        const result=oneAnswer(track,questions,q,o);
        assert.deepEqual(Array.from(result.axes),[50,50,50,50,50,50],`${track} ${q.id}: 중립 응답에 취향 점수 부여`);
      }
    }
  }
});

test('플랫폼·회피 조건은 실제 추천 후보를 필터링한다',()=>{
  const questions=engine.profileQuestions('gamer');
  const platformQ=questions[0],pc=platformQ.options[0];
  const platformResult=oneAnswer('gamer',questions,platformQ,pc);
  assert.ok(platformResult.recommendations.length>0);
  assert.ok(platformResult.recommendations.every(g=>g.platforms.includes('pc')));
  const avoidQ=questions[25],avoidOption=avoidQ.options[4];
  const avoidResult=oneAnswer('gamer',questions,avoidQ,avoidOption);
  assert.ok(avoidResult.prefs.avoid.includes('monetization'));
  assert.ok(avoidResult.recommendations.every(g=>!g.risks.includes('monetization')));
});


test('새로 보완한 무점수 선호 신호도 추천 점수에 반영된다',()=>{
  const cases=[
    ['gamer','p10',4],
    ['gamer','p14',4],
    ['gamer','p24',3],
    ['gamer','p30',4],
    ['nongamer','p4',3],
    ['nongamer','p24',3]
  ];
  for(const [track,qid,index] of cases){
    const questions=engine.profileQuestions(track),q=questions.find(x=>x.id===qid),o=q.options[index];
    const result=oneAnswer(track,questions,q,o);
    assert.ok(result.recommendations.length>0,`${track} ${qid}: 추천 없음`);
    assert.ok(result.recommendations.some(g=>Math.abs(g.metadataAdjustment)>0),`${track} ${qid}: 메타데이터 점수 미반영`);
  }
});
