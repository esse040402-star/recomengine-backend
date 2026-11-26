// DB 설계용 참조 자료를 코드에서 추출합니다. DB에 쓰거나 SQL을 실행하지 않습니다.
import {createServer} from 'vite';
import {writeFile,mkdir,readFile} from 'node:fs/promises';
const vite=await createServer({server:{middlewareMode:true},appType:'custom'});
try {
 const E=(await vite.ssrLoadModule('/src/services/preferenceEngine.js')).default;
 const catalog=JSON.parse(await readFile(new URL('../src/data/generated/catalog.json',import.meta.url),'utf8'));
 const surveys=[];
 for(const track of ['gamer','nongamer'])for(const [kind,questions] of [['QUICK',E.quickQuestions(track)],['PROFILE',E.profileQuestions(track)],['DEEP',E.deepQuestions(track,{})]]){
  surveys.push({surveyType:kind,track:track.toUpperCase(),templateVersion:3,adaptiveExample:kind==='DEEP',questions:questions.map((q,index)=>({clientQuestionKey:q.id,seq:index+1,fieldKey:q.field,title:q.title,maxSelect:q.max,options:q.options.map(o=>({clientOptionKey:o.id,label:o.label,isNone:!!o.prefs?.none}))}))});
 }
 const reference={notice:'DB 입력용 완성 시드가 아닌 프론트 참조입니다. DEEP은 답변에 따라 바뀌므로 run별 문항 스냅샷을 보존하세요. clientQuestionKey/clientOptionKey는 DB PK가 아닙니다.',schemaVersion:3,axes:E.AXES,games:catalog.map(g=>({clientGameKey:g.id,steamAppId:g.app,title:g.title})),surveys};
 await mkdir('../docs',{recursive:true});await writeFile('../docs/frontend-db-reference.json',JSON.stringify(reference,null,2)+'\n');
 console.log(`DB 참조 생성: 게임 ${catalog.length}개, 설문 ${surveys.map(s=>s.questions.length).join('/')}문항`);
} finally {await vite.close();}
