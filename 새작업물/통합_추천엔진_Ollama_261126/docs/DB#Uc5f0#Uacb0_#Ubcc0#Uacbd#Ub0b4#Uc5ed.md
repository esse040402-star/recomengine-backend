# RecomEngine 프론트엔드 연결 수정 내역

기준: 업로드된 recomengine-backend-main.zip (GitHub 아카이브 식별자 a025eb0db54e33f96489507bfeb829becf9f20f0), 기능명세서 및 백엔드 설계 문서 v1.0, 화면 설계 스토리보드.

## 이번 수정의 범위

화면 디자인, 설문 문구와 문항 수, 137개 게임 카탈로그, 로컬 추천 계산을 유지하면서 끊겨 있던 프론트 연결을 수정했습니다. 현재 FastAPI 서버의 실제 경로를 사용합니다. 문서의 새 `/api/v1` API와 정규화 DB 전체를 구현한 버전은 아닙니다. SQL 실행, 실제 Supabase 쓰기, GitHub 커밋·푸시는 하지 않았습니다.

## 실제 수정한 기능

| 문서 기능 / 화면 | 수정 내용 | 주요 파일 |
|---|---|---|
| ACC-09·12 / S-02·03·26 | 시작 시 쿠키 세션 복원, 가입 후 게스트 상태 이관, 변경 후 700ms 자동 저장, 요청 직렬화 | AppContext.jsx, accountService.js, stateSaveQueue.js |
| ACC-12 / S-26 | 실패한 저장 재시도, 계정별 로컬 저장, 미전송 복구본 보관 및 설정에서 복구 | AppContext.jsx, ProfilePage.jsx |
| ACC-04·07 / S-02·03 | 중복 가입/로그인 요청 차단, 폼에 오류 표시 | profileActions.js, DialogContents.jsx |
| SRV-11·CHT-07 / S-09·29 | 서버가 필수로 요구하는 28문항 blueprint 추가, AI 대기 55초, 실패 시 규칙 기반 대체 및 안내 | recommendationService.js |
| CHT / S-09 | 데이터 미반영 추천은 기존 프로필 컨텍스트를 전송하지 않음. 결과의 명시적 반영 흐름 유지 | guidedActions.js |
| SRV / S-04·29·30 | 설문 실행 client UUID, 시작·완료 시각, 트랙, PAGE/CHAT 출처 기록 | surveyActions.js, guidedActions.js |
| EXT·GAM-17 / S-20·21 | Steam 상태 확인, 리뷰 조건 재조회, cursor 다음 페이지, 중복 제거, 지난 요청 취소 | useSteamData.js, steamService.js |
| RNK-09·NWS / S-15·16 | 기존 새로 불러오기 버튼을 실제 시장 API에 연결, 데이터별 확인 시점 갱신 | useSteamData.js |
| GAM-01 / S-17~21 | 상세 진입 시 Steam 정보 갱신, 실패 시 내장 정보 유지 | useSteamData.js |
| COM·ONB / S-01 | 온보딩 접근 제한, 존재하지 않는 게임/경로 보정, 리뷰 별칭 | routes.js, App.jsx |
| SET-07 / S-26 | 로그인 중 설문 초기화해도 첫 화면으로 돌아갈 수 있게 수정 | surveyActions.js, App.jsx |
| GAM / S-17 | 이미지 갤러리의 게임 ID 누락 보완, 게임 탭 이동 후 돌아가기 대상 보존 | usePageController.jsx |
| RPT / S-31 | 연결이 없었던 프로필 인쇄 버튼 연결 | usePageController.jsx |
| 실행 환경 | 누락된 React index.html 추가, Vite API 프록시, FastAPI의 dist 제공 | index.html, vite.config.js, app/main.py, .gitignore |

계정으로 로그인할 때 기존 계정 상태가 없으면 빈 계정 상태로 시작합니다. 게스트 정보 이관은 회원가입 시에만 합니다. 다른 사람의 게스트 정보가 기존 계정에 자동으로 섞이지 않도록 한 처리입니다. 기존 서버에서는 가입과 상태 저장이 두 요청이므로 원자적 이관은 아닙니다. 이관 실패 시 미전송 복구본과 다시 저장 기능을 이용합니다.

## 현재 API와 새 DB API의 차이

| 작업 | 현재 연결된 API | 문서의 목표 API | DB 전환 시 작업 |
|---|---|---|---|
| 계정 | `/api/account/session`, `/login`, `/signup`, `/logout` | `/api/v1/auth/*` | name/id를 nickname/userId로 변환, 가입 guestState 원자적 이관 |
| 상태 | `PUT /api/account/state` | `GET/PUT /api/v1/me/state` | 서버 revision 발급, baseVersion 조건부 갱신, 409 충돌 처리 |
| AI 문항 | `POST /api/survey/generate` | `/api/v1/survey-runs/{id}/deep-questions` | 먼저 run 생성, run별 질문/선택지 스냅샷 저장 |
| 설문 저장 | 계정 상태에 초안·완료 결과 저장 | `/api/v1/survey-runs/*` | 질문별 응답 저장, 서버 검증과 점수 계산 |
| 찜·평가·피드백 | 계정 state에 함께 저장, 게스트는 로컬 | `/api/v1/me/saved-games`, `/feedbacks`, `/games/{id}/reviews` | 사용자 소유권 검사, 정규 테이블에 분리 저장 |
| Steam | `/api/market`, `/api/steam/reviews`, `/api/steam/details` | `/api/v1/rankings/steam`, `/games/{id}/steam-reviews` 등 | 응답 변환과 경로 전환 동시 진행 |
| 추천·리포트 | 프론트의 검증된 선택지 점수 계산 | `/api/v1/recommendations`, `/me/profile-report` | 서버에서 문항 원본을 기준으로 다시 계산 |

HTTP 클라이언트는 현재 `{error, detail}`와 새 `{code, message, details}` 오류 형식 및 본문 없는 204 응답을 모두 처리합니다. 그러나 서버가 아직 version을 반환하지 않기 때문에 서버 간 충돌 방지까지 구현됐다는 의미는 아닙니다. 현재 다중 기기 저장은 마지막 저장이 우선합니다.

## DB 담당자가 꼭 구분할 식별자

| 값 | 현재 의미 | DB 권장 처리 |
|---|---|---|
| state.version = 3 | 로컬 저장 형식 버전 | 낙관적 잠금용 revision과 별도 컬럼 사용 |
| runId | 이번 수정부터 생성되는 프론트 실행 UUID | 서버 run ID와 동일하다고 가정하지 말 것. client_run_key로 중복 방지 후 서버 ID 응답 |
| elden / stardew 등의 game.id | 프론트 게임 키 | games의 UUID PK와 별도 client_game_key 또는 매핑 테이블 사용 |
| game.app | Steam 앱 번호 | steam_app_id에 매핑. 클라이언트 키와 PK를 혼용하지 말 것 |
| q1 / d01 등의 question.id | 설문 내 문항 키 | 설문 유형 + 트랙 + 템플릿 버전 + 문항 키로 원본 구분 |
| 0 / 1 등의 option.id | 해당 질문 내부 선택지 키 | 질문 FK + 선택지 키가 유일해야 함. 전역 option PK가 아님 |
| review.id | 사용자가 작성한 로컬 평가 UUID | client_review_key를 둬 재전송 중복 방지. Steam review ID와 분리 |

`docs/frontend-db-reference.json`은 코드에서 추출한 137개 게임 키/Steam 앱 번호, 게이머·비게이머별 7·30문항, 28문항 예시입니다. 실제 DB에 바로 실행하는 SQL이나 확정 시드는 아닙니다. 아래 명령으로 다시 만들 수 있습니다.

```powershell
cd frontend
node tools/export-db-reference.mjs
```

## 데이터 관계와 보관 범위

- 회원은 프로필·설정·추천 조건 각 1개와 여러 설문 실행·찜·피드백·평가를 가집니다.
- 설문 실행은 유형 QUICK/DEEP/PROFILE, 트랙 GAMER/NONGAMER, 출처 PAGE/CHAT, 대화 모드 PROFILE/FRESH를 구분합니다.
- 설문 실행마다 당시 표시한 문항·선택지와 응답을 보관합니다. 동적 28문항은 같은 d25라도 응답에 따라 의미가 달라집니다. 공통 survey_questions 행 하나를 덮어쓰면 과거 리포트를 재현할 수 없습니다.
- 완료된 설문 결과와 미완료 초안은 별도입니다. 재응답을 시작해도 기존 완료 결과는 새 완료 전까지 유지합니다.
- 새 대화의 추천을 반영해도 기존 30문항 프로필·찜·평가·피드백은 유지해야 합니다. FRESH 추천 계산 중에는 기존 피드백과 조건을 제외합니다.
- 사용자가 선택한 피드백은 sentiment(좋음/싫음/관심없음)과 played, hidden 플래그를 분리합니다. 모든 값을 단일 enum으로 합치면 '재밌음 + 이미 플레이함'을 동시에 표현할 수 없습니다.
- 사용자 작성 평가는 rating(1~5), text, game, 작성 시각을 저장합니다. Steam의 긍정/부정 리뷰와 같은 평점 컬럼으로 합치지 마세요.
- Steam 가격은 현재 응답의 정수 단위를 그대로 보존하고 표시할 때만 100으로 나눕니다. currency와 수집 시각을 함께 보관하세요.
- 프론트의 축 점수와 적합도는 신뢰된 서버 결과가 아닙니다. DB 전환 후에는 서버의 문항/가중치 원본으로 재계산해야 합니다.

## 아직 서버 구현이 필요한 부분

1. 기능명세서 5장의 `/api/v1` 도메인 API와 정규화 테이블 연결.
2. 서버 revision 기반의 다중 기기 충돌 방지. 현 클라이언트의 직렬 저장은 한 탭의 요청 순서만 보장합니다.
3. 설문·피드백에 대한 서버 추천 계산과 스냅샷 관리. 현재 추천 가중치 반영은 프론트 엔진이며 외부 AI 모델 학습이 아닙니다.
4. 공용 유저 평가 게시. 현재 작성 평가는 개인 계정 상태에 저장되며 다른 회원에게 공개되지 않습니다.
5. 새 게임의 자동 카탈로그 편입. 현재 Steam API는 기존 137개 게임의 정보 갱신에 연결되어 있고 카탈로그 자체는 프론트에 포함된 자료입니다.
6. 로그인 만료·다중 기기 로그아웃 정책, HTTPS 쿠키/CSRF 정책의 실제 배포 검증.
7. 기존 데이터에 실행 ID나 작성 시각이 없으면 임의로 과거 값을 만들지 말고 레거시로 구분해 이관해야 합니다.

## 검증과 실행

`frontend/README.md`의 수정본 실행 방법을 참고하세요. 자동 테스트는 실제 Supabase에 쓰지 않습니다. 브라우저 테스트의 계정 요청은 실제 FastAPI mock DB 서버로, Steam·AI 응답은 재현 가능한 테스트 응답으로 검사합니다. 외부 Steam/Ollama의 실제 응답 품질과 실제 Supabase 쓰기는 이번 검증 범위에 포함하지 않습니다.

## 수정본 검증 결과

- 백엔드 mock 자동 테스트: 89개 통과.
- 프론트 통신·저장 순서·오류·화면 이동 테스트: 8개 통과.
- 브라우저: 7문항 완료, 회원가입·게스트 이관·세션 복원, 찜 저장, Steam 리뷰 조회·필터·더 보기, AI blueprint 전달과 프로필 미전송 모드, 저장 실패 후 새로고침·복구, 30문항 완료, 로그인 상태의 온보딩 초기화 확인.
- React 배포 빌드 성공. 내장 카탈로그·리뷰 자료로 인해 큰 JS 번들 경고는 남아 있습니다.
- 린트 오류는 없으나 기존 생성형 뷰 코드의 미사용 import 등 경고와 일부 Hook 의존성 경고는 남아 있습니다.
- 실제 Supabase·Ollama·Steam 외부 호출과 GitHub 반영은 하지 않았습니다.

## 적용할 때

기존 작업 폴더와 별도로 압축을 풀어 먼저 실행하세요. 압축에는 `.env`, `node_modules`, `.venv`, 빌드 산출물이 없습니다. 기존 API 키 파일을 덮어쓰지 마세요. 변경된 파일 전체 목록은 `docs/changed-files.txt`에 있습니다. 테스트 후 팀의 작업 브랜치에 해당 변경을 적용하시면 됩니다.
