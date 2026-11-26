# GitHub 새작업물 통합 상태 (2026-11-26)

기준: `esse040402-star/recomengine-backend`의 `main` 트리(확인한 SHA: `0342860e5243ebdb3ea99b579ae2d8cabd6a6476`)와 ZIP2 프로젝트 비교.

## 작업 영역별 상태

| GitHub 새작업물 | ZIP2 기준 상태 | 이번 통합 작업 |
|---|---|---|
| `API가중치_분류통합` | v5 6축 점수 JSON 생성물은 포함. 독립 vocabulary/normalization 전체 런타임 통합은 확인되지 않음 | v5 게임 점수를 Supabase `game_trait_scores`로 옮기는 importer 추가. 외부 후보의 태그는 원본 Steam/IGDB 표현을 유지 |
| `API통합_설문가중치` | 설문·추천 엔진 일부 로직은 현재 프로젝트에 존재. 독립 quick API 흐름 전체가 같은 방식으로 반영된 것은 아님 | 현재 7문항/30문항 프로필 흐름을 유지하고 AI 모드에서 프로필 조건 반영 |
| `Steam_추가게임_59개` | CSV/미디어 데이터 미포함 | DB에 별도 적재 필요. 외부 Render 카탈로그는 실시간 후보 공급원으로 사용 |
| `개인페이지` | 프로필 페이지와 관련 UI/저장 코드 존재. standalone SQLite 전달본과 동일한 구현은 아님 | 기존 앱 구현 유지 |
| `게임정보_API테스트` | Render API 클라이언트와 별도 외부 게임 라우트 존재 | AI 대화 추천 경로에서 Render 검색 결과를 실제 후보로 병합하도록 연결 |
| `게임정보_수집` | 1,284개 점수 파일은 포함되나 원본 `games.json/csv`는 미포함 | 점수 importer는 기존 `games.steam_app_id`로 연결. 원본 게임 데이터 적재는 별도 필요 |
| `설문_수정핵심` | 수정표 자체가 적용 코드가 아닌 제안 문서. 현재 앱에는 7문항/30문항이 존재 | 현재 앱 문항 수와 모바일 전용 선택지 제거 상태를 확인 |
| `스팀ID_게임태그조회` | 독립 `game_tags.py`는 미포함. Render 상세 데이터와 Steam 서비스 코드 존재 | Render 상세 응답의 Steam/IGDB 장르·태그·플랫폼을 AI 후보용 필드로 평탄화 |
| `스팀리뷰_API수정` | ZIP2의 `steam.py`는 구형 `/appreviews` 호출 사용 | 공식 `IUserReviewsService/GetAppReviews/v1/`로 리뷰 조회·집계·페이지 함수 교체 및 계약 테스트 추가 |
| `첫7문항` | 별도 폴더 전체는 미포함. 앱의 `preferenceEngine.js`에 7문항 게이머/비게이머 흐름 존재 | 기존 통합 UI 유지. 모바일 전용 옵션은 현재 사용 경로에서 제외 |
| `최신 업데이트_261117` | 주요 기능 상당수 반영. `account.py`, `accounts.py`, `mock_db.py`, `preferenceEngine.js`, guest-session 관련 파일 일부는 Git blob SHA 일치. 일부 survey/docs/profileActions/test 파일은 차이 존재 | 기존 ZIP2 파일을 무조건 덮어쓰지 않고 현재 버전을 보존. AI 통합 변경을 추가 |
| `회원가입_비회원진단_데이터저장개선` | 계정·게스트 세션 연결 기능이 프로젝트에 상당 부분 존재 | 현재 계정 흐름을 유지. 이 작업에서 DB/migration은 실행하지 않음 |

## 이번에 추가·수정한 핵심

- 대화형 AI의 `profile` / `conversation` 모드 구분
- 모드 선택 시 이전 대화 기록 초기화
- conversation 모드에서 저장 프로필을 API 요청에 넣지 않고 서버에서도 무시
- Ollama가 실제 게임 제목 후보를 생성하고 Render API에서 존재 여부·상세정보를 조회
- Render 후보와 Supabase 게임 후보를 합치고 중복 제목 제거
- Render 실패 시 기존 Supabase 후보로 대체
- profile 모드에서 DB 게임별 6축 벡터를 우선 읽고, 없으면 기존 규칙 벡터로 대체
- v5 1,284개 게임 점수를 Steam AppID로 Supabase에 적재하는 별도 스크립트
- Steam 리뷰 API를 공식 신규 엔드포인트로 변경
- PC·콘솔 지원 여부 확인 및 모바일 전용 게임 제외 유지

## 남은 외부 검증 및 데이터 작업

1. Windows PC에서 `python -m scripts.check_render_game_api`를 실행해 Render `/`, `/docs`, `/api/status`, 검색, 상세 응답을 확인합니다.
2. Supabase `games` 테이블에 1,284개 및 추가 59개 AppID가 적재되어 있는지 확인합니다. 이 프로젝트는 실제 DB를 수정하지 않았습니다.
3. `python -m scripts.import_game_trait_scores --dry-run`으로 AppID 매칭 수를 확인합니다.
4. Ollama `qwen2.5:7b` 실제 실행으로 두 모드의 대화→후보 검색→추천 이유를 브라우저에서 확인합니다.
5. 전체 프론트엔드 `npm run build`를 Windows에서 실행합니다. 현재 개발 컨테이너에는 Windows용 Rolldown 네이티브 모듈만 있어 Linux 빌드를 실행할 수 없습니다.
6. 로그인/비회원/설문/개인페이지와 추천 화면의 전체 브라우저 회귀 테스트를 진행합니다.

## 중요한 범위 제한

- 이 작업은 Supabase 운영 DB를 변경하지 않았습니다.
- Render API가 현재 온라인인지 이 개발 컨테이너에서는 실시간 확인할 수 없었습니다.
- GitHub `main`에 업로드하거나 커밋하지 않았습니다.
- GitHub의 독립 데이터 파일(1,284개 원본, 추가 59개 CSV/미디어)을 ZIP2에 자동 복사하지 않았습니다. 해당 파일들은 위 링크를 통해 별도 적재해야 합니다.
