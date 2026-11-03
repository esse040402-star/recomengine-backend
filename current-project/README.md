> **프론트는 React(Vite) 프로젝트입니다 (2026-10-08~).** 화면까지 보려면 아래 **'6단계'** 를 따르세요. 예전 단일 HTML 프로토타입을 서버에 붙이던 방식(`scripts/patch_frontend.py`)은 더 이상 쓰지 않습니다. React 프론트 자체의 실행·테스트는 [frontend/README.md](frontend/README.md), 변경 내용과 DB 준비 자료는 [docs/DB연결_변경내역.md](docs/DB연결_변경내역.md)에 있습니다. 서버 API 경로는 기존 그대로입니다.

# RecomEngine 백엔드 (FastAPI + Supabase + Ollama + RAWG/IGDB)

## 팀원용 빠른 확인 가이드 (받기 → 실행 → 확인)
이 백엔드를 처음 받은 팀원이 **API 키도, 실제 DB도 없이** 제대로 동작하는지 확인하는 순서입니다 (약 10분).
기본 설정(`USE_MOCK_DB=true`)은 **메모리 가짜 DB**를 쓰므로 팀의 Supabase에는 아무것도 쓰지 않고, 서버를 끄면 데이터가 사라집니다.

**준비물**: Windows + VS Code(PowerShell 터미널), [Git](https://git-scm.com), Python 3.12 또는 3.13 권장
(저장소 주소가 열리지 않으면 GitHub 초대를 요청하세요)

### 1단계. 받기
```powershell
git clone https://github.com/esse040402-star/recomengine-backend.git
cd recomengine-backend
```

### 2단계. 설치
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # 줄 맨 앞에 (.venv) 가 보이면 성공
py -m pip install -r requirements.txt
copy .env.example .env                # 그대로 두면 됩니다 (USE_MOCK_DB=true, 키 비어 있음)
```
- `Activate.ps1` 실행이 막히면 한 번만: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- 설치가 실패하면 Python 버전을 확인하세요 (`py --version`). 3.14 에서 안 되면 3.12/3.13 으로 `.venv` 를 다시 만드세요.

### 3단계. 자동 테스트로 한 번에 확인
```powershell
python -m pytest
```
- **모두 `passed` 로 끝나면 정상**입니다 (현재 90개, 경고 1개는 무시해도 됩니다). 약 10초 걸립니다.
- API 테스트는 항상 가짜 DB로 실행되고 외부 서비스도 가짜로 바꿔 쓰므로 키·인터넷·Ollama 가 필요 없습니다.

### 4단계. 서버 켜기
```powershell
fastapi dev app/main.py
```
브라우저에서 http://localhost:8000/api/status 를 열어 아래처럼 나오는지 봅니다 (끄려면 터미널에서 `Ctrl+C`).

| 항목 | 키 없이 받았을 때 정상 값 | 뜻 |
|---|---|---|
| `mock_db` | `true` | 가짜 DB로 동작 중 |
| `feeds` | `true` | 스팀 랭킹·뉴스 조회 가능 (키 불필요, 인터넷만 있으면 됨) |
| `ai`, `ollama.up` | `false` | Ollama 를 안 깔았으면 정상. 규칙 기반으로 대신 동작 |
| `rawg`, `igdb`, `steam` | `false` | 해당 API 키를 안 넣었다는 뜻. 정상 |

### 5단계. http://localhost:8000/docs 에서 눈으로 확인
각 항목을 펼치면 `Try it out` 이 이미 눌려 있어서 `Execute` 만 누르면 됩니다.

| 확인할 것 | 어떻게 | 정상이면 |
|---|---|---|
| 게임 목록 | `GET /api/games` (q 에 `elden` 입력해도 됨) | 샘플 게임 19개 |
| 취향 진단 흐름 | 아래 'Swagger(/docs)에서 해볼 순서' 1~4번 | 점수·리포트·추천 10개가 나옴 |
| 스팀 인기 순위 | `GET /api/market` → section=`rankings` | 순위 10개 (인터넷 필요) |
| 게임 소식·할인 | `GET /api/market` → section=`news` | `news`, `newReleases`, `sales` 가 채워짐 |
| 스팀 리뷰·정보 | `GET /api/steam/reviews`, `GET /api/steam/details` → game=`elden` | 리뷰 12개 / 개발사·가격 |
| 회원가입·로그인 | `POST /api/account/signup` → `login` | 가짜 DB 안에서 동작 (서버를 끄면 사라짐) |
| 오류 형식 | `GET /api/market` → game=`없는게임`, section=`news` | 404 와 `{"error": "한국어 메시지"}` |

### 6단계 (선택). 프론트 화면까지 보기
저장소에 들어 있는 React 프론트(`frontend/`)를 빌드해서 이 서버로 함께 띄웁니다. **Node.js 20 이상**이 필요합니다 (`node -v` 로 확인).
```powershell
cd frontend
npm ci                      # 처음 한 번 (package-lock.json 기준으로 설치)
npm run build               # frontend/dist 생성 (약 1초)
cd ..
$env:USE_MOCK_DB="true"     # 실제 DB 대신 가짜 DB (처음엔 꼭 이렇게)
fastapi dev app/main.py     # → http://localhost:8000
```
- 반드시 **http://localhost:8000** 으로 여세요. 로그인은 쿠키 방식이라 서버와 같은 주소여야 합니다. `frontend/dist` 가 없으면 서버는 API 만 제공하고 화면(`/`)은 나오지 않습니다.
- 프론트 코드를 고치며 볼 때는 터미널 2개로 서버(위)와 `cd frontend; npm run dev` 를 함께 켜고 **http://localhost:5173** 으로 엽니다 (Vite 가 `/api` 를 8000번 서버로 넘겨 줍니다).
- 게임 뉴스·랭킹은 처음에는 프론트에 저장된 자료(2026-09-30)가 보이고, **"새로 불러오기"** 를 누르면 스팀 최신 자료로 바뀝니다.
- 스팀 **인기 순위**(`/api/market?section=rankings`)는 스팀의 차트 주소가 오류(500)를 내면 서버도 502 를 돌려주고, 화면은 저장된 자료를 그대로 두고 안내 토스트를 보여 줍니다. 2026-10-09 에 한동안 이런 스팀 쪽 오류가 있었다가 복구되어 지금은 정상입니다. 뉴스·리뷰·상세는 영향이 없습니다.
- 순위·뉴스가 이상하면 프론트 게임 목록이 바뀐 것일 수 있습니다 → 아래 '6. 스팀 랭킹·뉴스' 의 대응표 갱신 명령 참고.

### 7단계 (선택). 키가 있어야 하는 기능
`.env` 를 열어 해당 줄만 채우고 서버를 다시 켭니다. **키는 개인 메시지로만 전달하고, `.env` 는 절대 깃허브·단체방에 올리지 마세요.**

| 기능 | 필요한 설정 |
|---|---|
| 게임 데이터 수집 (RAWG/IGDB) | `RAWG_API_KEY`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`, 관리자 호출용 `ADMIN_TOKEN` |
| 스팀 내 라이브러리 가져오기 | `STEAM_API_KEY` |
| AI 설문·추천 문장 | Ollama 설치 + 모델 내려받기 (아래 'Ollama 사용법') |
| 실제 DB 연결 | `USE_MOCK_DB=false` + `SUPABASE_*` 키. **DB 담당자와 합의 전에는 쓰기 작업 금지** (`sql/` 도 먼저 확인) |

#### API 키 발급받는 법
키는 모두 **무료**로 받을 수 있고, 받은 값은 `.env` 의 해당 줄에만 붙여 넣습니다 (따옴표·띄어쓰기 없이 `이름=값`). 저장한 뒤 **서버를 껐다 다시 켜야** 적용됩니다.
> 사이트 화면은 바뀔 수 있으니, 아래와 다르면 각 사이트 안내를 따르세요.

**① RAWG — `RAWG_API_KEY`** (게임 이름·장르·태그·표지 수집)
1. https://rawg.io/apidocs 에서 **Get API Key** 를 누르고 가입(이메일)합니다.
2. 로그인 후 같은 페이지에 나오는 키를 복사해 `RAWG_API_KEY=` 뒤에 붙입니다.
- 무료는 **월 20,000회, 비상업용**입니다. 검색 1회 + 게임 하나당 2회를 쓰므로 수업 프로젝트에는 충분합니다.
- 서비스 화면에 RAWG 출처 표시(링크)를 하라는 조건이 있습니다. 실제로 공개 배포할 때 확인하세요.

**② IGDB — `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`** (출시일·평점 등 보강 정보)
IGDB는 Twitch 계정으로 키를 받습니다.
1. https://www.twitch.tv 에서 가입하고 **이메일 인증**을 마칩니다.
2. Twitch 계정 설정에서 **2단계 인증(2FA)을 켭니다.** (꺼져 있으면 개발자 콘솔에서 앱을 만들 수 없습니다. 켠 뒤 콘솔 페이지를 새로고침하세요.)
3. https://dev.twitch.tv/console 접속 → **Applications** 탭 → **Register Your Application**.
4. 입력합니다.
   - **Name**: 다른 사람과 겹치지 않는 이름 (예: `recomengine-본인이름`)
   - **OAuth Redirect URLs**: `http://localhost` (이 프로젝트는 로그인 연동을 쓰지 않아 아무 주소나 괜찮습니다)
   - **Category**: 목록에서 `Application Integration` 등 맞는 것을 고릅니다
   - CAPTCHA를 풀고 **Create**
5. 만들어진 앱의 **Manage** 를 눌러 **Client ID** 를 복사 → `IGDB_CLIENT_ID=`
6. 같은 화면의 **New Secret** 을 눌러 나온 값을 복사 → `IGDB_CLIENT_SECRET=` (**다시 볼 수 없으니** 바로 복사해 두세요. 잃어버리면 New Secret 으로 새로 만들면 됩니다.)
- 서버가 이 두 값으로 접근 토큰을 알아서 받아 갑니다. 토큰은 직접 만들 필요 없습니다.
- 무료 사용 조건과 호출 한도는 IGDB 공식 문서(https://api-docs.igdb.com)에서 확인하세요.

**③ Steam — `STEAM_API_KEY`** (내 스팀 라이브러리 가져오기에만 필요)
1. 스팀에 로그인한 상태로 https://steamcommunity.com/dev/apikey 에 접속합니다.
2. **Domain Name** 에는 `localhost` 처럼 적고(이 프로젝트는 도메인을 쓰지 않습니다), 약관에 동의한 뒤 **Register** 를 누릅니다.
3. 나온 **Key** 를 복사해 `STEAM_API_KEY=` 뒤에 붙입니다.
- 결제 이력이 거의 없는 **'제한된 계정'** 은 키 발급이 안 될 수 있습니다 (스팀 정책이라 직접 확인 필요).
- **스팀 인기 순위·뉴스·할인·리뷰·가격은 이 키가 필요 없습니다.** 키는 '내 라이브러리' 조회에만 씁니다.
- 라이브러리를 가져오려면 스팀 프로필의 **게임 세부 정보가 '공개'** 여야 하고, **SteamID64(17자리 숫자)** 가 필요합니다. 프로필 주소가 `/profiles/숫자` 형태면 그 숫자이고, 아니면 https://steamid.io 에서 프로필 주소를 넣어 `steamID64` 를 확인합니다.

**④ 관리자 토큰 — `ADMIN_TOKEN`** (게임 수집 같은 관리자 API 보호용, 아무 문자열이나 직접 만듭니다)
```powershell
python -c "import secrets;print(secrets.token_urlsafe(32))"
```
나온 값을 `ADMIN_TOKEN=` 뒤에 붙입니다. 비워 두면 관리자 API 가 꺼집니다. `SESSION_SECRET` 도 같은 방법으로 만들어 채웁니다 (**`USE_MOCK_DB=false` 면 필수**, 비우면 서버가 시작되지 않음).

**잘 들어갔는지 확인**
| 확인 | 방법 | 정상이면 |
|---|---|---|
| 키가 읽혔는지 | http://localhost:8000/api/status | `rawg`, `igdb`, `steam` 이 `true` (**값이 들어 있는지만** 알려 줄 뿐, 키가 올바른지는 아래에서 확인) |
| RAWG 키가 맞는지 | `/docs` → `POST /api/admin/games/sync`, 헤더 `X-Admin-Token` 에 `ADMIN_TOKEN` 값, 본문 `{"query": "elden ring", "limit": 3}` | 200 과 `saved` 에 게임 제목이 나옴. 키가 틀리면 502 + "API 키를 확인하세요" |
| IGDB 키가 맞는지 | 위 동기화 직후 `GET /api/games` (q=`elden`) 결과의 `igdb_id` | 숫자가 채워져 있음. **`null` 이면 IGDB 키 문제**입니다 (RAWG 와 함께 쓸 때 IGDB 실패는 오류로 안 보이고 건너뛰어서, 서버 터미널에 `IGDB 보강 실패` 경고가 뜹니다) |
| Steam 키가 맞는지 | `/docs` → `POST /api/ai/backlog`, 본문 `{"steam_id": "내 17자리 번호"}` | 내 게임 기반 결과(`candidates_considered` > 0). 키가 틀리면 502, 프로필·게임 목록이 비공개면 422(게임 목록 없음), 키를 안 넣었으면 503 |
- ⚠️ **`USE_MOCK_DB=true`(기본값)일 때만** 위 게임 수집(동기화)을 마음대로 해 보세요. 가짜 DB(메모리)에만 저장되고 서버를 끄면 사라집니다. `false` 로 바꾸면 팀의 실제 DB 에 저장되니 DB 담당자와 먼저 상의하세요. (Steam 확인에 쓰는 `backlog` 는 DB 에 저장하지 않습니다.)
- 키가 채팅·스크린샷·깃허브에 노출됐다면 **즉시 해당 사이트에서 키를 다시 발급(재생성)** 하세요. 이 서버는 오류 로그에 키가 찍히지 않게 처리해 두었지만, 직접 붙여 넣은 것까지는 막을 수 없습니다.

### 자주 막히는 곳
| 증상 | 해결 |
|---|---|
| `fastapi` 명령을 찾을 수 없음 | 가상환경이 꺼진 상태. `.\.venv\Scripts\Activate.ps1` 을 다시 실행 |
| `ModuleNotFoundError: No module named 'app'` | `backend` 폴더(저장소 맨 위)에서 실행했는지 확인 |
| 8000 번 포트가 이미 사용 중 | 이미 켜진 서버를 `Ctrl+C` 로 끄거나 `fastapi dev app/main.py --port 8001` |
| `ai: false` 인데 문제인가요? | Ollama 를 안 쓰면 정상입니다. 규칙 기반으로 동작합니다 |
| 스팀 순위·뉴스에서 502 | 인터넷 연결 또는 스팀 일시 장애. 잠시 후 다시 시도 (서버가 10~30분 결과를 보관합니다) |
| 서버를 껐더니 데이터가 사라짐 | mock 모드의 정상 동작입니다 |

---

## 0. Mock 모드로 먼저 돌려보기 (Supabase·프론트 없이)
`.env` 에 `USE_MOCK_DB=true` 가 있으면 메모리 내 가짜 DB(샘플 게임 19개 포함)로 동작합니다.
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
`http://localhost:8000/docs` 의 모든 API(25개)에 **제목 옆 한국어 설명(괄호)**, 상세 설명, 성공/실패 응답 예시를 붙였습니다.
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

## 프론트(프로토타입) 대응 사항
프론트가 서버에 요구하는 것과, 그에 맞춰 백엔드를 바꾼 내용입니다. (React 프론트 기준으로 정리 · 예전 HTML 프로토타입 때의 설명이 일부 남아 있습니다)

| 프로토타입에서 달라진 점 | 백엔드 대응 |
|---|---|
| 회원가입/로그인/로그아웃, 계정에 화면 상태 저장 (`/api/account/*`) | `app/routers/account.py` 추가. Supabase Auth로 가입/로그인, 로그인 상태는 서명된 HttpOnly 쿠키 |
| 실패 응답의 `{"error": "..."}` 를 그대로 화면에 표시 | 모든 오류를 `{"error": 한국어 메시지, "detail": ...}` 형식으로 통일 (FastAPI 기본은 `detail`만 줌) |
| `/api/survey/generate` 에 `blueprint`(28문항 원본), `request`(사용자가 쓴 문장), `profileContext` 를 보냄 | 요청 스키마에 반영하고 프롬프트의 참고 자료(데이터)로만 사용. React 프론트는 `blueprint` 를 이미 보냅니다. AI 가 바꾼 제목이 **다른 문항의 원래 제목과 겹치면 쓰지 않고 원문을 유지**합니다 (겹치면 프론트 검증이 28문항 전체를 버리기 때문, `survey_ai.sanitize`) |
| 기본 7문항의 선택지/최대 선택 수 변경, `lowSpec`, 불호 `monetization` 추가 | 추천 계산에 `lowSpec`(가산점), `monetization`(보수적 태그 제외) 반영 |

### 계정 API 규격 (프론트가 호출하는 형태 그대로)
| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/api/account/session` | - | `{user: {id,name,email}\|null, state?}` (`email` 은 프로필 화면에 표시) |
| POST | `/api/account/signup` | `{name,email,password(8자+)}` | `201 {user}` (+쿠키). state 없음 → 프론트가 현재 게스트 상태 사용 |
| POST | `/api/account/login` | `{email,password}` | `{user, state?}` (+쿠키) |
| POST | `/api/account/logout` | - | `{ok:true}` (쿠키 삭제) |
| PUT | `/api/account/state` | `{state:{...}}` (1MB 이하) | `{ok:true}` (로그인 필요) |

- **같은 주소에서 서빙해야 쿠키가 동작합니다.** `frontend/` 를 빌드(`npm run build`)한 뒤 `http://localhost:8000` 으로 여세요 (위 '6단계'). 개발 중에는 Vite(`http://localhost:5173`)가 `/api` 를 8000번으로 넘겨 주므로 같은 방식으로 동작합니다. 프론트 `VITE_API_BASE_URL` 로 다른 주소의 서버를 가리키려면 `.env` 의 `CORS_ORIGINS` 에 프론트 주소(예: `http://localhost:5173`)를 추가해야 합니다.
- 로그인 8회 연속 실패하면 15분간 429, 회원가입은 같은 IP에서 10분에 10번 넘게 시도하면 429 (프로세스 메모리 기준). 로그아웃은 쿠키를 지우는 방식이라, 쿠키가 유출됐다면 만료(`SESSION_DAYS`)까지 유효합니다.
- `SESSION_SECRET` 은 **실제 DB 모드(`USE_MOCK_DB=false`)에서 필수**입니다. 비어 있으면 서버가 시작되지 않고 만드는 방법을 알려 줍니다. 가짜 DB 모드에서는 비워 둬도 되지만, 그때는 재시작할 때마다 전원 로그아웃됩니다. HTTPS로 배포하면 `COOKIE_SECURE=true`.
- 실제 Supabase 모드에서는 `SUPABASE_ANON_KEY` 도 필요하고, **`sql/002_user_states.sql`(새 테이블 1개)을 DB 담당자와 합의 후 실행**해야 합니다. 가입 때 이메일 인증 없이 바로 활성화됩니다(`email_confirm=true`).
### 프론트 담당자에게 전달할 것
프론트가 서버에 맞추는 데 필요한 수정은 이미 반영돼 있습니다(`blueprint` 전송, 계정 API 경로 등). 남은 확인·수정 요청은 **[docs/프론트엔드_수정_요청서_20261009.md](docs/프론트엔드_수정_요청서_20261009.md)** 에 정리했습니다. 가장 중요한 것은 아래입니다.
- 저사양·과금 피로 등 **제외 요소를 고르면 추천이 0건**이 됩니다. 카탈로그에 `lowSpec: true` 게임이 0개이고, `riskCoverage` 에 `monetization` 이 있는 게임이 0개이며, 그 밖의 제외 요소도 Steam 파생 게임 121개가 모두 빠져 큐레이션 15개만 남습니다 (코드와 데이터로 계산한 값).

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

## 3. 프론트 연결
React 프론트는 저장소의 `frontend/` 에 있습니다. 빌드하고 서버와 함께 띄우는 방법은 위 **'6단계'** 와 [frontend/README.md](frontend/README.md) 를 보세요.
(`scripts/patch_frontend.py` 는 예전 단일 HTML 프로토타입용이라 더 이상 쓰지 않습니다.)

## 4. 실행
```powershell
fastapi dev app/main.py        # http://localhost:8000  (API 문서: /docs)
```
Ollama 설정은 위 'Ollama 사용법'을 참고하세요.

## 5. 게임 데이터 채우기 (RAWG + IGDB)
`/docs` 에서 `POST /api/admin/games/sync` 에 `X-Admin-Token`(= .env 의 ADMIN_TOKEN)을 넣고
`{"query": "elden ring", "limit": 5}` 처럼 호출하면 games 테이블에 저장됩니다.

## 6. 스팀 랭킹·뉴스 (게임 id 대응표)
프론트는 게임을 자기 id(`elden`, `portal` …)로 부르고, 스팀에 물어보려면 앱 번호가 필요합니다. 그 대응표는 `data/catalog_apps.json` 에 있고
프론트의 `frontend/src/data/generated/catalog.json`(게임 목록)과 `marketSnapshot.json`(저장된 뉴스)에서 뽑아 만듭니다. **프론트의 게임 목록이 바뀌면 다시 실행하세요.**
```powershell
python -m scripts.export_catalog
```
다른 위치의 프론트 데이터 폴더를 쓰려면 `python -m scripts.export_catalog "C:\경로\frontend\src\data\generated"` 처럼 폴더를 지정합니다.
- 게임을 지정하지 않은 '전체 뉴스'는 대표 게임 12개(`news_games`)의 공식 소식을 보여줍니다.
- 스팀 공개 주소만 쓰므로 별도 키가 필요 없고, 응답은 서버 메모리에 잠깐 보관됩니다(서버를 다시 켜면 비워짐).

## API 요약
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | /api/status | 프론트가 부팅 때 호출 (ai: Ollama 켜짐+모델 설치됨, feeds: 스팀 실시간 조회 사용 가능 = 항상 true) |
| GET | /api/market?section=rankings\|news\|reviews[&game=id] | 스팀 인기 순위 · 소식/신작/할인 · 리뷰 집계 (결과를 10~30분 보관, DB 저장 없음) |
| GET | /api/steam/reviews?game=id&sentiment&days&language&sort&cursor | 스팀 리뷰 목록 (12개씩, cursor 로 이어 받기) |
| GET | /api/steam/details?game=id | 스팀 가격·사양·한국어 지원 갱신 |
| GET/POST/PUT | /api/account/* | 회원가입·로그인·상태 저장 (위 표 참고) |
| POST | /api/survey/generate | 심화 설문 28문항을 Ollama로 다듬기 (request, profileContext, blueprint 사용) |
| GET | /api/games, /api/games/{id} | 게임 검색/상세 |
| POST | /api/sessions | 진단 세션 시작 |
| PUT | /api/sessions/{id}/answers | 답변 저장 |
| POST | /api/sessions/{id}/complete | 점수·리포트·추천 생성 후 저장 |
| GET | /api/sessions/{id}/result | 결과 조회 |
| POST | /api/admin/games/sync | RAWG/IGDB → games 동기화 |
