# RecomEngine React

사용자 설문으로 플레이 성향을 분석하고 Steam 카탈로그, 랭킹, 뉴스, 리뷰와 연결하는 RecomEngine의 React/Vite 전환본입니다. 기존 프로토타입의 화면 구조와 설문 흐름, 게임 테마, 사이드바·다크모드·게임 상세 흐름을 실제 JSX 컴포넌트와 전역 상태로 분리했습니다.

## 실행

Node.js 24 LTS와 npm을 사용합니다.

```bash
npm ci
npm run dev
npm run build
```

서버 환경변수가 없어도 추출된 Steam 스냅샷으로 게스트 모드가 실행됩니다. FastAPI를 연결할 때는 `.env`에 `VITE_API_BASE_URL=http://localhost:8000`을 추가합니다. 계정·AI 동적 설문·Steam 최신 자료 요청은 서비스 경계에서 호출되며, 서버가 없을 때 임의의 로그인 성공을 표시하지 않습니다.

## 라우트

HashRouter를 사용하므로 정적 호스팅에서도 새로고침 문제가 없습니다.

| 경로 | 기능 |
| --- | --- |
| `#/welcome` | 게스트 진입, 게이머/비게이머 선택, 계정 연결 |
| `#/survey/quick` | 첫 7문항 빠른 취향 찾기 |
| `#/result` | 첫 추천 5개 |
| `#/deep-intro`, `#/survey/deep` | 빠른 답변 기반 28문항 맞춤 설문 |
| `#/report`, `#/survey/preference` | 30문항 플레이 성향 프로필 |
| `#/home` | 중앙 AI 추천 대화, 카루셀, 고정 추천 목록 |
| `#/explore`, `#/rankings`, `#/news` | 탐색 필터, Steam 랭킹 카테고리, 뉴스·세일 |
| `#/profile` | 찜한 게임, 프로필, 내 활동, 설정 |
| `#/game/:id`, `#/game/:id/reviews`, `#/game/:id/requirements` | 전체 게임 상세, 리뷰 필터, 시스템 사양 |

## 구조

- `src/state`: Context/reducer와 localStorage(`recom-integrated-v3`) 영속 상태
- `src/hooks`: 설문·대화·프로필 액션 및 화면 컨트롤러
- `src/pages`, `src/components`: 실제 JSX 페이지와 공통 UI
- `src/services`: 추천 엔진, 게임/Steam 스냅샷, 계정·피드백 API 경계
- `src/data/generated`: 카탈로그·상세·리뷰·이미지 매핑
- `src/styles/prototype.css`, `public/assets`: 기존 CSS와 로컬 이미지·폰트

런타임 HTML 문자열이나 `dangerouslySetInnerHTML`을 사용하지 않습니다. 큰 카탈로그와 base64 이미지는 데이터 파일 및 실제 이미지 파일로 분리했습니다.

## FastAPI 연결 지점

- `POST /api/survey/generate`
- `GET /api/market?section=rankings|news|reviews`
- `GET /api/steam/details?game=:id`
- `GET /api/steam/reviews?game=:id&sentiment=&language=&sort=&days=`
- `POST /api/account/login`, `POST /api/account/signup`, `GET /api/account/session`

프론트엔드는 `recommendationService`, `steamService`, `accountService`를 통해서만 외부 DTO를 사용하며, 연결 전에는 스냅샷으로 동작합니다. 데스크톱·모바일에서 quick7 → result → home → detail/reviews, 프로필 설정, 다크모드, 사이드바 접기, 카루셀 이동을 확인한 뒤 `npm run build`를 통과시키면 됩니다.
