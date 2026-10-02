# RecomEngine 백엔드 (FastAPI + Supabase + Ollama + RAWG/IGDB)

## 0. Mock 모드로 먼저 돌려보기 (Supabase·프론트 없이)
`.env` 에 `USE_MOCK_DB=true` 가 있으면 메모리 내 가짜 DB(샘플 게임 14개 포함)로 동작합니다.
- 서버를 끄면 데이터가 사라집니다. 이 모드에서는 `supabase` 패키지가 설치되지 않아도 됩니다.
- `fastapi dev app/main.py` 후 http://localhost:8000/docs 에서 API를 직접 눌러 테스트하세요.
- 로그인 흉내: `Authorization: Bearer mock-<이름>` 헤더 (예: `Bearer mock-alice`)
- 자동 테스트: `python -m tests.test_mock_db`, `python -m tests.test_ai_features`, `python -m tests.test_prototype_sync`, `python -m tests.test_docs_coverage`, `python -m tests.test_search_quality`, `python -m tests.test_swagger_korean`, `python -m tests.test_game_clean` (Ollama 불필요) / `python -m pytest` (API 전체, 가짜 Ollama 사용)
- Ollama가 꺼져 있으면 리포트는 규칙형으로 대체되고, `/api/survey/generate` 는 503을 돌려줍니다.
- 실제 DB로 바꿀 때: `USE_MOCK_DB=false` + `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 입력

### Swagger(/docs)에서 해볼 순서
1. `POST /api/sessions` → `{"track":"gamer"}` → 응답의 `id` 복사
2. `PUT /api/sessions/{id}/answers` → `{"answers":[{"question_id":"q1","answer":["0"]}]}`
3. `POST /api/sessions/{id}/complete` → `{"axes":[90,50,60,60,15,70],"prefs":{"platforms":["pc"],"avoid":["horror"]}}`
4. `GET /api/sessions/{id}/result`

## Ollama 사용법 (로컬 AI) — Windows 기준
1. https://ollama.com 에서 설치 파일을 받아 설치합니다. 설치 후 작업 표시줄에 Ollama가 떠 있으면 서버가 켜진 상태입니다.
2. 모델 내려받기 (VS Code 터미널):
   ```powershell
   ollama pull qwen2.5:7b      # 한국어 성능이 좋은 모델 (약 4.7GB, 메모리/VRAM 8GB 이상 권장)
   ollama pull qwen2.5:3b      # PC 사양이 낮을 때 (약 2GB)
   ```
   문서에 정리한 다른 후보: `llama3.1:8b`, `gemma2:9b`, `gemma2:2b`
3. 동작 확인: `ollama run qwen2.5:7b` 로 한국어 질문을 해보고 `/bye` 로 종료
4. 서버 확인: 브라우저에서 http://localhost:11434 → "Ollama is running"
5. `.env` 의 `OLLAMA_MODEL` 을 내려받은 모델 이름과 똑같이 맞춥니다 (예: `qwen2.5:7b`)
6. 백엔드를 켜고 http://localhost:8000/api/status 의 `ollama.model_ready` 가 `true` 인지 확인
- 첫 호출은 모델을 메모리에 올리느라 느립니다. 이후 10분(`OLLAMA_KEEP_ALIVE`)은 빠릅니다.
- 현재 올라간 모델 확인: `ollama ps` / 설치된 모델: `ollama list`
- GPU가 없으면 느려서 심화 설문 생성(50초 제한)이 실패할 수 있습니다. 이 경우 프론트는 기본 문항으로 자동 대체됩니다. 3b 모델을 써보세요.
- Ollama가 꺼져 있어도 서버는 죽지 않고, 규칙 기반 결과로 대체됩니다 (`source: "rule"`). 리뷰 요약만 AI가 필수라 503을 돌려줍니다.

## AI 기능 API (AI 활용방안 문서 기준)
| 기능 | 경로 | 비고 |
|---|---|---|
| 자연어 검색 / 대체제 찾기 | `POST /api/ai/search` | "스위치 없는데 동물의 숲 같은 게임 없어?" |
| 비슷한 게임 찾기 | `POST /api/ai/similar` | 제목 + 선호(indie, cheap, recent...) |
| 추천 이유 설명 | `POST /api/ai/explain` | 결과를 recommendations.reason 에 저장 |
| 백로그 처리반 | `POST /api/ai/backlog` | 게임 제목 목록 또는 steam_id(STEAM_API_KEY 필요) |
| 플레이타임 계산기 | `POST /api/ai/schedule` | "주말에 하루 2시간씩" |
| 리뷰 장단점 요약 | `POST /api/ai/review-summary` | reviews 직접 전달 또는 steam_app_id |
| 할인/출시예정 상단 노출 | `GET /api/ai/deals?session_id=` | games.price_info 필요 |
| 가격 동기화(관리자) | `POST /api/ai/admin/sync-prices` | 스팀 가격 -> price_info |

역할 분담: 문장 이해/작성은 Ollama, 점수·필터·일정 계산은 코드가 합니다. Ollama 출력은 항상 검증하고, 실패하면 규칙 기반으로 대체합니다.

## Swagger(/docs) 한국어 설명
`http://localhost:8000/docs` 의 모든 API(22개)에 **제목 옆 한국어 설명(괄호)**, 상세 설명, 성공/실패 응답 예시를 붙였습니다.
- 그룹(태그)마다 한국어 설명이 있고, 요청 입력칸에는 **바로 실행해 볼 수 있는 예시 값**과 항목별 설명이 들어 있습니다.
- 각 항목은 `Try it out` 이 이미 눌려 있어서 `Execute` 만 누르면 됩니다.
- 설명을 고치고 싶으면 **`app/docs.py` 한 파일만** 수정하세요. (입력 항목 설명은 `app/schemas.py`)
- 새 API를 추가하고 설명을 빼먹으면 `python -m tests.test_docs_coverage` 가 알려줍니다.
- Swagger 자체의 영어 문구(Parameters, Execute, Responses, Response body, Schema 등)와 데이터 종류(string, integer…) 옆에도 한국어가 붙습니다. 번역은 **`app/static/swagger_ko.js` 의 `LABELS`** 에서 고칠 수 있습니다. 예시 JSON과 입력칸은 바꾸지 않습니다.

## 게임 데이터 정리 & 코드 점검 (실제 RAWG/IGDB 응답 확인 후 반영)
회귀 테스트: `python -m tests.test_game_clean`

| 항목 | 내용 |
|---|---|
| 장르 이름 통일 | IGDB `Platform` → `Platformer`, `Role-playing (RPG)` → `RPG`, `Turn-based strategy (TBS)` → `Strategy` + 태그 `Turn-Based` 등 |
| 기능 태그 제거 | `Steam Achievements`, `Full controller support`, `Steam Cloud`, `steam-trading-cards`, `Controller` 등 게임 성향과 무관한 태그 |
| 비공식 항목 제외 | 평가 5개 미만 + 추가 50명 미만 + 메타크리틱 없음 → 건너뛰고 응답의 `skipped` 에 표시 (`include_minor: true` 로 해제) |
| 스팀 앱 id 저장 | RAWG 판매처 목록에서 스팀 주소를 찾아 `steam_app_id` 저장 → 리뷰 요약·가격 동기화가 RAWG로 가져온 게임에서도 동작 |
| **API 키 노출 차단** | httpx가 요청 주소(`?key=...`)를 터미널 로그에 찍던 문제, 오류 메시지에 키가 담기던 문제 수정 |
| 1000행 제한 대응 | Supabase는 한 번에 1000행만 돌려줘서 게임이 많아지면 추천·검색이 일부 게임만 보던 문제 → 나눠서 끝까지 읽음 |
| 과금 불호 | `In-App Purchases` 태그도 과금 피로(monetization) 제외 대상에 추가 |
| 외부 API 오류 안내 | RAWG 키가 틀리면 502 + "키를 확인하세요", 인터넷 문제면 503 (예전엔 500 + 터미널에 키가 담긴 오류) |

- 게임 하나를 가져올 때 RAWG 요청이 1번 늘었습니다(판매처 조회). 무료 한도(월 20,000회) 안에서 충분합니다.
- 정리 기준(기능 태그 목록, 비공식 항목 기준, 장르 이름 대응표)은 `app/services/game_clean.py` 상수에서 조정하세요.
- **이미 저장된 게임에는 적용되지 않습니다.** mock 모드는 서버를 다시 켜면 비워지니 다시 Sync 하면 되고, 실제 DB는 같은 게임을 다시 Sync 하면 덮어써집니다.

## 검색 정확도 보정 (AI 응답 분석 후 반영)
실제 7B 응답을 분석해서 발견한 문제를 고쳤습니다. (회귀 테스트: `python -m tests.test_search_quality`)

| 발견한 문제 | 수정 |
|---|---|
| "동물의 숲"을 영어 제목으로 못 바꿔 `liked_games` 가 비어 있음 | **`data/game_aliases.json` 한국어 별칭표**(58개). 코드가 먼저 찾고, 표에 없으면 AI가 추측. 자유롭게 추가하세요 |
| 질문에 없는 `indie`/`cheap`/`Puzzle` 등을 AI가 지어내 순위가 왜곡됨 | 선호(인디·할인·최근…)는 **문장에 키워드가 있을 때만** 반영, 기기는 문장에 **실제로 언급된 것만** 인정, 기준 게임이 있으면 AI가 고른 장르/태그는 무시 |
| 무관한 게임(호러 등)이 목록에 섞임 | `Singleplayer` 같은 **흔한 태그의 가중치를 낮추고**, 1등의 30% 미만 점수는 결과에서 제외 (샘플 DB에서는 결과가 2~3개로 줄어듭니다) |
| 추천 이유에 AI가 없는 말을 지어냄 ("추리 퍼즐") | AI 문장에 **게임 제목이 [대괄호]로 없거나**, 게임 태그로 뒷받침되지 않는 장르·분위기 주장(추리, 퍼즐, 협동, 농장 등 16종)이 있으면 버리고 기본 문장 사용. 점수가 낮은 결과에는 AI 설명 생략 |

> 유사도는 장르·태그 겹침으로 계산해서, 샘플 데이터(19개)에서는 "동물의 숲 같은 게임"에 Overcooked! 2가 Stardew Valley보다 위에 나올 수 있습니다. RAWG 실데이터를 넣은 뒤 다시 확인하고 `GENERIC_TAGS`, 가중치 상수를 조정하세요 (`app/services/ai_features.py`).

## 새 프로토타입(화면_프로토타입_진) 대응 사항
이전 프로토타입과 비교해서 달라진 부분과, 그에 맞춰 백엔드를 바꾼 내용입니다.

| 프로토타입에서 달라진 점 | 백엔드 대응 |
|---|---|
| 회원가입/로그인/로그아웃, 계정에 화면 상태 저장 (`/api/account/*`) | `app/routers/account.py` 추가. Supabase Auth로 가입/로그인, 로그인 상태는 서명된 HttpOnly 쿠키 |
| 실패 응답의 `{"error": "..."}` 를 그대로 화면에 표시 | 모든 오류를 `{"error": 한국어 메시지, "detail": ...}` 형식으로 통일 (FastAPI 기본은 `detail`만 줌) |
| `/api/survey/generate` 에 `request`(사용자가 쓴 문장), `profileContext` 추가, 호출 지점이 2곳으로 증가 | 요청 스키마에 반영하고 프롬프트의 참고 자료(데이터)로만 사용. `scripts/patch_frontend.py` 가 두 호출 지점을 패치 |
| 기본 7문항의 선택지/최대 선택 수 변경, `lowSpec`, 불호 `monetization` 추가 | 추천 계산에 `lowSpec`(가산점), `monetization`(보수적 태그 제외) 반영 |

### 계정 API 규격 (프론트가 호출하는 형태 그대로)
| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/api/account/session` | - | `{user: {id,name}\|null, state?}` |
| POST | `/api/account/signup` | `{name,email,password(8자+)}` | `201 {user}` (+쿠키). state 없음 → 프론트가 현재 게스트 상태 사용 |
| POST | `/api/account/login` | `{email,password}` | `{user, state?}` (+쿠키) |
| POST | `/api/account/logout` | - | `{ok:true}` (쿠키 삭제) |
| PUT | `/api/account/state` | `{state:{...}}` (1MB 이하) | `{ok:true}` (로그인 필요) |

- **같은 주소에서 서빙해야 쿠키가 동작합니다.** `backend/frontend/index.html` 에 넣고 `http://localhost:8000` 으로 여세요. HTML 파일을 더블클릭해서 열면 계정 기능은 막혀 있습니다(프론트가 안내함).
- 로그인 8회 연속 실패하면 15분간 429 (프로세스 메모리 기준). 로그아웃은 쿠키를 지우는 방식이라, 쿠키가 유출됐다면 만료(`SESSION_DAYS`)까지 유효합니다.
- `.env` 에 `SESSION_SECRET` 을 꼭 채우세요(없으면 재시작할 때마다 전원 로그아웃). HTTPS로 배포하면 `COOKIE_SECURE=true`.
- 실제 Supabase 모드에서는 `SUPABASE_ANON_KEY` 도 필요하고, **`sql/002_user_states.sql`(새 테이블 1개)을 DB 담당자와 합의 후 실행**해야 합니다. 가입 때 이메일 인증 없이 바로 활성화됩니다(`email_confirm=true`).
- 이미 프론트 쪽에 Node 서버(`Steam_시작.bat`)로 계정 API를 만들어 두었다면 겹치니, 어느 쪽을 쓸지 먼저 정하세요.

### 프론트 담당자에게 전달할 것
1. `/api/survey/generate` 요청 body 에 `blueprint: E.publicBlueprint(track, answers)` 한 줄 추가 (호출 2곳). 직접 고치지 않으면 `python -m scripts.patch_frontend "<html 경로>"` 로 자동 패치할 수 있습니다.
2. 아래 두 선택지를 고르면 프론트의 `recommend()` 가 거의 항상 빈 결과를 낼 수 있습니다(코드와 카탈로그 데이터를 읽어서 확인한 내용이고, 화면에서 실행해 보지는 않았습니다).
   - 비게이머 Q1 "일반 사무용 컴퓨터/노트북" → `lowSpec` 을 요구하지만 카탈로그 137개 중 `lowSpec: true` 인 게임이 0개
   - 불호 "P2W/과금 피로" → `monetization` 이 `riskCoverage` 에 있어야 통과하는데 0개

## 1. 설치 (VS Code 터미널, backend 폴더에서)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env        # 열어서 키를 채우세요
```
> 패키지 설치가 실패하면 Python 3.14가 원인일 수 있습니다. 3.12 또는 3.13으로 가상환경을 만들어 보세요.

## 2. DB 준비 (실제 Supabase 연결 시에만)
1. Supabase SQL Editor에서 `sql/001_constraints.sql` 실행
2. 설문 문항 넣기: `python -m scripts.seed_survey_questions`

## 3. 프론트 연결 (프론트 담당자와 합의 후)
```powershell
python -m scripts.patch_frontend "C:\경로\화면_프로토타입_진.html"   # backend/frontend/index.html 생성 (blueprint 2곳 패치)
```

## 4. 실행
```powershell
fastapi dev app/main.py        # http://localhost:8000  (API 문서: /docs)
```
Ollama 설정은 위 'Ollama 사용법'을 참고하세요.

## 5. 게임 데이터 채우기 (RAWG + IGDB)
`/docs` 에서 `POST /api/admin/games/sync` 에 `X-Admin-Token`(= .env 의 ADMIN_TOKEN)을 넣고
`{"query": "elden ring", "limit": 5}` 처럼 호출하면 games 테이블에 저장됩니다.

## API 요약
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | /api/status | 프론트가 부팅 때 호출 (ai: Ollama 켜짐+모델 설치됨, feeds) |
| GET/POST/PUT | /api/account/* | 회원가입·로그인·상태 저장 (위 표 참고) |
| POST | /api/survey/generate | 심화 설문 28문항을 Ollama로 다듬기 (request, profileContext, blueprint 사용) |
| GET | /api/games, /api/games/{id} | 게임 검색/상세 |
| POST | /api/sessions | 진단 세션 시작 |
| PUT | /api/sessions/{id}/answers | 답변 저장 |
| POST | /api/sessions/{id}/complete | 점수·리포트·추천 생성 후 저장 |
| GET | /api/sessions/{id}/result | 결과 조회 |
| POST | /api/admin/games/sync | RAWG/IGDB → games 동기화 |
