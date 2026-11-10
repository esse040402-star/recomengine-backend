# 게임정보 API 테스트

기존 코드와 분리한 Python/FastAPI 서버입니다. 키 없이 먼저 배포한 뒤 Render 환경변수를 등록할 수 있습니다.

## Render 입력값

| 항목 | 값 |
|---|---|
| Language | Python 3 |
| Branch | main |
| Root Directory | 새작업물/게임정보_API테스트 |
| Build Command | pip install -r requirements.txt |
| Start Command | uvicorn main:app --host 0.0.0.0 --port $PORT |
| Health Check Path | /health |
| Compute | Free (첫 연결 테스트) |

배포 후 표시되는 실제 onrender.com 호스트명을 Steam API 키 발급 도메인에 입력합니다.
Render → Environment에서 STEAM_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET을 등록하고 재배포합니다.
키를 코드·GitHub·브라우저에 넣지 않습니다. IGDB access token은 서버가 자동 발급하고 만료 전 갱신합니다.

## 화면과 API

- `/`: 팀원용 테스트 화면
- `/health`: 서버 실행 확인
- `/api/status`: 키 등록 여부(실제 유효성은 조회로 확인), 목록 수집 상태
- `/api/games?q=elden&page=1`: 전체 Steam 목록 기반 검색. 최초 요청 시 자동 수집
- `/api/games/1245620`: Steam 상세·태그·리뷰 + IGDB 매칭 정보
- `/api/catalog/sync` POST: 목록 수집 실패 후 재시도
- `/docs`: API 설명과 직접 실행

## 수집 범위

Steam IStoreService/GetAppList의 게임 전체 페이지를 순회합니다. 고정된 샘플 게임 목록은 사용하지 않습니다. 수집 도중 검색은 현재까지 받은 목록을 대상으로 합니다. 상세정보를 모든 게임에 대해 한꺼번에 호출하지 않고 선택할 때 조회합니다.

Steam 상점 appdetails: 이름, 가격, 장르, 지원 기능, 플랫폼, 사양, 언어, 출시일, 이미지 등 반환 원문.
Steam 사용자 태그: 상점 HTML의 app_tag를 읽습니다. 공식 Web API 태그 엔드포인트가 아니며 상점 구조·접근 제한에 따라 조회되지 않을 수 있습니다.
Steam 리뷰: appreviews 응답. IGDB: Steam AppID에 맞는 게임의 장르, 테마, 키워드, 모드, 시점, 플랫폼, 평점, 클리어 시간(초).
장르/태그/테마는 출처별로 구분합니다. 사양 원문을 임의로 고사양/저사양으로 판단하거나 누락값을 만들어 채우지 않습니다.

## 운영 범위

이번 작업은 게임정보 연결 테스트입니다. 로그인·설문·가중치 계산·DB·Ollama는 포함하지 않습니다.
현재 목록/상세 캐시는 메모리에 저장되어 재시작 시 다시 조회합니다. 영구 데이터 수집은 추후 DB 연결 단계입니다.
외부 서비스의 키 권한·지역·호출 제한에 따라 실패할 수 있으며 실패를 화면에 표시합니다.
공개 테스트용 읽기 API이므로 URL을 아는 사람도 조회할 수 있습니다. 장기 운영 전 팀 인증과 사용자별 요청 제한을 추가하세요.

## 로컬 검증

Python 3.12 이상:
```
pip install -r requirements.txt
pip install pytest
python -m pytest tests -q
uvicorn main:app --host 127.0.0.1 --port 8000
```
.env.example은 변수명 참고용입니다. 로컬에서는 실행 환경변수로 직접 지정합니다.

## 출처 문서
- https://partner.steamgames.com/doc/webapi/IStoreService
- https://api-docs.igdb.com/
- https://render.com/docs/deploy-fastapi
