# Steam 추가 게임 59개 (2026-11-25)

기존 622개와 중복되지 않는 신규 59개만 포함합니다. 기존 데이터 전체를 교체하지 않고, 실제 DB에 없는 AppID만 추가하는 용도입니다.

- `games_additional.csv`: 기존 게임 CSV와 동일한 열 이름·순서입니다. Steam 기본 정보와 리뷰 집계를 포함합니다. IGDB 미수집 항목은 공란이며, 기존 DB 값이 있으면 공란으로 덮어쓰지 않습니다.
- `additional_media.json`: 같은 59개 AppID의 Steam 스크린샷 URL 및 조회 당시 가격 응답입니다. `steam_app_id`로 연결합니다. 스크린샷은 `source_data.steam_refresh.screenshots`에 넣을 수 있습니다. 가격은 수집 당시 참고값이며, 미국 상점에서 보완한 3개는 가격을 제외했습니다.

등록 전 실제 DB의 `steam_app_id`와 다시 비교하고 이미 있는 행은 건너뛰세요. 리뷰 본문은 포함하지 않습니다.
