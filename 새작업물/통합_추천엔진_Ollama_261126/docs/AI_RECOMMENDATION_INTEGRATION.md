# RecomEngine 대화형 AI 추천 통합 메모

## 추천 모드

- `mode="profile"`: 프론트엔드가 기존 빠른 취향/플레이 성향 설문 요약(`profile_context`)을 전달합니다. 플랫폼·불호 조건을 적용하고, 사용자 6축 벡터와 게임별 `game_trait_scores` 벡터를 비교합니다.
- `mode="conversation"`: `profile_context`를 서버에서 무시합니다. 현재 대화 이력만 Ollama와 검색 의도 분석에 전달해 취향을 누적합니다.
- 모드를 바꾸면 프론트엔드에서 기존 대화 기록을 비워 두 모드의 데이터가 섞이지 않게 합니다.

## Render 게임 API

서비스 기본 주소: `https://recomengine-game-api.onrender.com`
문서: `https://recomengine-game-api.onrender.com/docs`

대화형 추천이 준비 상태가 되면 Ollama가 실제 게임 제목 후보(`candidate_titles`)를 최대 5개 반환합니다. 백엔드는 각 제목을 Render의 `/api/games?q=...` 검색으로 확인하고 상세정보(`/api/games/{appid}`)를 받아 내부 DB 후보와 합칩니다. 외부 서버가 실패하면 내부 DB 후보로 계속 진행합니다.

Render 응답의 실제 운영 상태·필드 값은 실행 환경에서 확인해야 합니다. 외부 서버의 실시간 검증을 통과한 것으로 간주하지 않습니다. Windows/로컬 PC에서 `python -m scripts.check_render_game_api`를 실행하면 홈·Swagger·상태·검색·상세 API를 한 번에 점검할 수 있습니다.

## 1,284개 게임 점수 적용

`새작업물/게임취향_점수생성/개선_결과_v5/game_trait_scores_v5.json`은 1,284개 게임의 Steam AppID와 6축 점수를 보유합니다. `scripts/import_game_trait_scores.py`는 이를 기존 `games.steam_app_id`와 연결해 `game_trait_scores`에 넣습니다.

실제 Supabase 적용 전 권장 순서:

1. Supabase `games` 테이블에 수집 게임 정보가 먼저 존재하고 `steam_app_id`가 연결되어 있는지 확인합니다.
2. `.env`에서 실제 Supabase 연결을 설정하고 `USE_MOCK_DB=false`인지 확인합니다.
3. `python -m scripts.import_game_trait_scores --dry-run`으로 매칭 개수와 누락 AppID 수를 확인합니다.
4. 설문 선택지·가중치 및 기본 태그 규칙까지 함께 준비할 때는 `python -m scripts.seed_trait_model`을 실행합니다. 이 스크립트는 기본 태그 점수를 갱신한 뒤 v5 점수를 다시 덮어써 최종 반영합니다.

점수 import는 `games` 행이나 사용자 설문 답변을 수정하지 않습니다. 매칭된 게임의 기존 `game_trait_scores` 행만 교체합니다. v5에서 근거가 없는 축은 null로 두기 위해 해당 축의 이전 점수 행을 삭제하고 새 행을 만들지 않습니다.

현재 ZIP2에는 1,284개 점수 JSON은 포함되어 있으나, 별도 GitHub 작업물인 [수집 원본 games.json](https://github.com/esse040402-star/recomengine-backend/blob/main/새작업물/게임정보_수집/data/collected/games.json)과 [추가 59개 CSV](https://github.com/esse040402-star/recomengine-backend/blob/main/새작업물/Steam_추가게임_59개/games_additional.csv), [추가 미디어 JSON](https://github.com/esse040402-star/recomengine-backend/blob/main/새작업물/Steam_추가게임_59개/additional_media.json)은 ZIP2에 포함되어 있지 않습니다. Supabase의 games 테이블에 필요한 Steam AppID가 아직 없다면 먼저 해당 데이터를 적재해야 합니다. DB 적용은 사용자가 직접 진행합니다. Render API의 전체 검색 카탈로그는 별도 후보 공급원으로 계속 사용합니다.

## 테스트 상태

- 백엔드 전체 pytest: 통과 여부는 최종 실행 결과로 기록합니다.
- 프론트엔드 Node 테스트: 통과 여부는 최종 실행 결과로 기록합니다.
- Render API 실시간 응답과 로컬 Ollama 실제 대화는 개발 환경에서 별도 검증이 필요합니다.
