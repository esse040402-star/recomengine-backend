// 실행 전: FastAPI(mock DB, 8000)와 Vite(5173)를 켜세요.
// Playwright 설치: npm install --no-save playwright && npx playwright install chromium
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.setDefaultTimeout(12000);page.on('pageerror',e=>{errors.push(e.message);console.error('화면 오류:',e.message);});
 await page.route('**/api/status',r=>r.fulfill({json:{feeds:true,ai:true}}));
 let blueprintCalls=0;await page.route('**/api/survey/generate',async r=>{const b=r.request().postDataJSON();assert.equal(b.blueprint.length,28);assert.equal(b.profileContext,undefined);assert.ok(b.request.length<=300);blueprintCalls++;await r.fulfill({json:{questions:b.blueprint,source:'ollama'}});});
 let reviewCalls=0;await page.route('**/api/steam/reviews?*',async r=>{const u=new URL(r.request().url());reviewCalls++;await r.fulfill({json:{items:[{id:'review-'+u.searchParams.get('cursor'),positive:true,created:Math.floor(Date.now()/1000),language:'koreana',text:'테스트용 Steam 리뷰입니다.',hours:10,helpful:5,url:'https://store.steampowered.com/app/1245620/'}],cursor:u.searchParams.get('cursor')==='*'?'next':null,checkedAt:new Date().toISOString()}});});
 await page.route('**/api/steam/details?*',r=>r.fulfill({json:{details:{}}}));
 await page.goto('http://127.0.0.1:5173/#/profile');await page.waitForURL('**/#/welcome');console.log('시작 화면 확인');
 // 게스트 7문항을 실제 버튼으로 완료
 await page.locator('[data-action="track"][data-value="gamer"]').click();
 for(let i=0;i<7;i++){console.log('빠른 설문',i+1);await page.waitForFunction(i=>JSON.parse(localStorage.getItem('recom-integrated-v3')).drafts.quick.index===i,i);await page.locator('[data-action="answer"]').first().click();await page.locator('[data-action="next"]').click();}
 await page.waitForURL('**/#/result').catch(async e=>{console.log('진단',await page.evaluate(()=>({url:location.hash,state:JSON.parse(localStorage.getItem('recom-integrated-v3'))})));throw e;});console.log('빠른 설문 결과 확인');
 const counts=await page.evaluate(async()=>{const E=(await import('/src/services/preferenceEngine.js')).default;return ['gamer','nongamer'].map(t=>[E.quickQuestions(t).length,E.deepQuestions(t,{}).length,E.profileQuestions(t).length]);});assert.deepEqual(counts,[[7,28,30],[7,28,30]]);
 await page.goto('http://127.0.0.1:5173/#/profile');await page.locator('[data-action="profile-tab"][data-value="settings"]').click();
 console.log('회원가입 시작');await page.locator('[data-action="account-signup"]').click();
 await page.locator('#account-form [name="name"]').fill('검증 플레이어');await page.locator('#account-form [name="email"]').fill('test'+Date.now()+'@example.com');await page.locator('#account-form [name="password"]').fill('test-password-123');
 const saved=page.waitForResponse(r=>r.url().includes('/api/account/state')&&r.request().method()==='PUT');
 await page.locator('[data-action="account-submit"]').click();await saved;await page.waitForURL('**/#/home');
 await page.reload();await page.waitForSelector('[data-screen="home"] h1');
 // 세션 복원 및 찜 자동 저장
 await page.goto('http://127.0.0.1:5173/#/game/elden');
 const save=page.waitForResponse(r=>r.url().includes('/api/account/state')&&r.request().method()==='PUT');await page.locator('[data-action="save"][data-id="elden"]').first().click();await save;
 await page.reload();await page.waitForSelector('[data-screen="game"]');
 assert.ok(await page.evaluate(()=>Object.keys(localStorage).some(k=>k.includes(':account:')&&JSON.parse(localStorage[k]).saved.includes('elden'))));
 // 리뷰 필터는 네트워크 재조회, 더 보기는 다음 cursor
 await page.goto('http://127.0.0.1:5173/#/game/elden/reviews');await page.locator('[data-action="steam-reviews-refresh"]').click();await page.getByText('테스트용 Steam 리뷰입니다.',{exact:true}).first().waitFor();
 await page.locator('[data-action="steam-reviews-more"]').click();await page.waitForFunction(()=>document.querySelectorAll('.steam-review-card').length===2);
 await page.locator('.review-filters select').first().selectOption('positive');await page.waitForFunction(()=>document.querySelectorAll('.steam-review-card').length===1);assert.ok(reviewCalls>=3);
 // AI 요청 검증: 점수는 로컬 선택지에 유지, fresh에는 기존 프로필 미전달
 const ai=await page.evaluate(async()=>{const E=(await import('/src/services/preferenceEngine.js')).default;const {generateSurvey}=await import('/src/services/recommendationService.js');const session={track:'gamer',quick:{completed:true,schema:2,answers:{}}};const result=await generateSurvey(session,'테스트',{includeProfileContext:false});return {length:result.questions.length,source:result.source,values:result.questions[0].options[0].values};});assert.equal(ai.source,'ollama');assert.equal(ai.length,28);assert.ok(ai.values && typeof ai.values==='object');assert.equal(blueprintCalls,1);
 // 전송 실패 자료는 새로고침 후에도 복구 가능
 await page.goto('http://127.0.0.1:5173/#/profile');await page.locator('[data-action="profile-tab"][data-value="settings"]').click();
 await page.route('**/api/account/state',r=>r.fulfill({status:503,json:{error:'테스트 저장 실패'}}));
 await page.locator('[data-action="mode"][data-value="dark"]').click();await page.locator('[data-action="account-retry-save"]').waitFor();
 await page.reload();await page.locator('[data-action="profile-tab"][data-value="settings"]').click();await page.locator('[data-action="account-recover-local"]').waitFor();
 await page.unroute('**/api/account/state');const recovered=page.waitForResponse(r=>r.url().includes('/api/account/state')&&r.request().method()==='PUT');await page.locator('[data-action="account-recover-local"]').click();await recovered;
 assert.equal(await page.evaluate(()=>document.documentElement.dataset.mode),'dark');
 // 프로필 30문항 완주
 await page.locator('[data-action="profile-tab"][data-value="play-profile"]').click();await page.locator('[data-action="start"][data-kind="preference"]').click();
 for(let i=0;i<30;i++){await page.waitForFunction(i=>Object.keys(localStorage).some(k=>k.includes(':account:')&&JSON.parse(localStorage[k]).drafts.preference?.index===i),i);await page.locator('[data-action="answer"]').first().click();await page.locator('[data-action="next"]').click();}
 await page.waitForURL('**/#/report');
 // 로그인 상태에서도 프로토타입 초기화는 첫 화면 유지
 await page.goto('http://127.0.0.1:5173/#/profile');await page.locator('[data-action="profile-tab"][data-value="settings"]').click();await page.locator('[data-action="restart-onboarding"]').click();await page.locator('[data-action="confirm-restart"]').click();await page.waitForURL('**/#/welcome');
 await page.screenshot({path:process.env.SCREENSHOT_PATH||'/tmp/recom-verified.png'});assert.equal(errors.length,0,errors.join('\n'));console.log('브라우저 검증 통과: 7/28/30문항, 계정 가입·복원·저장, 리뷰 조회·필터·페이지, AI blueprint, 초기화');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
