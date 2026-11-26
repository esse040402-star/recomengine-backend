import csv
import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

AXES = (
    "physical", "strategy", "exploration",
    "emotion", "comfort", "competition"
)

FIELDS = (
    ("steam.genres", "steam_genres"),
    ("igdb.keywords", "steam_categories"),
    ("igdb.genres", "igdb_genres"),
    ("igdb.themes", "igdb_themes"),
    ("igdb.keywords", "igdb_keywords"),
    ("igdb.game_modes", "igdb_game_modes"),
    ("igdb.player_perspectives", "igdb_player_perspectives"),
)

COMPETITION_WEIGHTS = {
    "tag:competitive": 95,
    "tag:esports": 95,
    "tag:moba": 90,
    "category:battle_royale": 85,
}

# ?????? ?? ??? ???? ??? ?? Trait? ?? ???? ??
AXIS_EXCLUSIONS = {
    "physical": {
        "category:pvp", "category:online_pvp", "tag:difficult"
    },
    "exploration": {
        "tag:crafting"
    },
    "comfort": {
        "category:co_op", "category:online_co_op",
        "category:single_player", "tag:crafting"
    },
}

# ?? ?? ????? ?? ??? ???? ??? ??? ??
STRATEGY_WEIGHT_OVERRIDES = {
    "genre:strategy": 75.0
}

def load_rules(sql_path, aliases, key):
    sql = sql_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*'((?:[^']|'')*)'\s*,\s*'([^']+)'\s*,\s*([0-9.]+)\s*\)"
    )

    rules = defaultdict(dict)
    connected = 0
    unmatched = []

    for tag, trait, weight in pattern.findall(sql):
        tag = tag.replace("''", "'")
        trait = trait.strip().lower()
        code = aliases.get(key(tag))

        if trait not in AXES:
            continue

        if not code:
            unmatched.append((tag, trait, float(weight)))
            continue

        rules[code][trait] = float(weight)
        connected += 1

    return rules, connected, unmatched


def collect_codes(game, resolve):
    codes = set()
    source_map = defaultdict(set)

    for source, field in FIELDS:
        for value in game.get(field) or []:
            result = resolve(source, value)
            code = result.get("code")

            if code:
                codes.add(code)
                source_map[code].add(field)

    # 수집 데이터에서 확인된 IGDB 철자 오류 보정
    for value in game.get("igdb_keywords") or []:
        if str(value).strip().casefold() == "competitve":
            codes.add("tag:competitive")
            source_map["tag:competitive"].add("igdb_keywords")

    return codes, source_map


def confidence(count):
    if count == 0:
        return "none"
    if count == 1:
        return "low"
    if count <= 3:
        return "medium"
    return "high"


def main():
    if len(sys.argv) != 5:
        raise SystemExit(
            "사용법: script.py NORMALIZER_DIR GAME_JSON SQL_FILE OUTPUT_DIR"
        )

    normalizer_dir = Path(sys.argv[1])
    game_file = Path(sys.argv[2])
    sql_file = Path(sys.argv[3])
    output_dir = Path(sys.argv[4])

    sys.path.insert(0, str(normalizer_dir))
    from normalization import resolve, key, ALIASES

    data = json.loads(game_file.read_text(encoding="utf-8"))
    games = data.get("games", [])

    if not isinstance(games, list):
        raise ValueError("games.json의 games 항목이 배열이 아닙니다.")

    rules, connected, unmatched = load_rules(sql_file, ALIASES, key)

    results = []
    distributions = {axis: Counter() for axis in AXES}
    evidence_totals = Counter()
    typo_count = 0

    for game in games:
        codes, source_map = collect_codes(game, resolve)

        if any(
            str(value).strip().casefold() == "competitve"
            for value in (game.get("igdb_keywords") or [])
        ):
            typo_count += 1

        scores = {}
        evidence = {}
        confidences = {}

        for axis in AXES:
            matched = []

            if axis == "competition":
                # PvP와 Online PvP는 하나의 지원 신호로 처리
                if (
                    "category:pvp" in codes
                    or "category:online_pvp" in codes
                ):
                    matched.append({
                        "code": "pvp_support",
                        "weight": 65.0,
                        "sources": sorted(
                            source_map.get("category:pvp", set())
                            | source_map.get("category:online_pvp", set())
                        ),
                    })

                for code, weight in COMPETITION_WEIGHTS.items():
                    if code in codes:
                        matched.append({
                            "code": code,
                            "weight": float(weight),
                            "sources": sorted(source_map.get(code, set())),
                        })

                # 경쟁 근거는 가장 강한 신호를 사용
                score = max(
                    (item["weight"] for item in matched),
                    default=None
                )

            else:
                for code in sorted(codes):
                    if code in AXIS_EXCLUSIONS.get(axis, set()):
                        continue

                    weight = rules.get(code, {}).get(axis)

                    if axis == "strategy":
                        weight = STRATEGY_WEIGHT_OVERRIDES.get(code, weight)

                    if weight is not None:
                        matched.append({
                            "code": code,
                            "weight": float(weight),
                            "sources": sorted(source_map.get(code, set())),
                        })

                score = (
                    round(
                        sum(item["weight"] for item in matched) / len(matched),
                        2
                    )
                    if matched else None
                )

            scores[axis] = score
            evidence[axis] = matched
            confidences[axis] = confidence(len(matched))

            if score is not None:
                distributions[axis][score] += 1
                evidence_totals[axis] += 1

        title = (
            game.get("steam_name")
            or game.get("igdb_name")
            or game.get("title")
            or "이름 없음"
        )

        results.append({
            "steam_app_id": game.get("steam_app_id"),
            "igdb_id": game.get("igdb_id"),
            "title": title,
            "scores": scores,
            "confidence": confidences,
            "evidence_count": {
                axis: len(evidence[axis]) for axis in AXES
            },
            "score_evidence": evidence,
            "canonical_codes": sorted(codes),
        })

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "game_trait_scores_v2.json"
    csv_path = output_dir / "game_trait_scores_v2.csv"
    report_path = output_dir / "검증보고서_v2.md"

    payload = {
        "meta": {
            "game_count": len(results),
            "rule_count_connected": connected,
            "rule_count_unmatched": len(unmatched),
            "typo_corrections": typo_count,
            "axes": list(AXES),
            "missing_score_policy": "null_when_no_evidence",
            "competition_policy": "max_signal_pvp_support_65",
            "version": 2,
            "axis_exclusions": {k: sorted(v) for k, v in AXIS_EXCLUSIONS.items()},
            "strategy_weight_overrides": STRATEGY_WEIGHT_OVERRIDES,
        },
        "games": results,
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "steam_app_id", "igdb_id", "title",
            *AXES,
            *[axis + "_evidence_count" for axis in AXES],
            *[axis + "_confidence" for axis in AXES],
        ])

        for item in results:
            writer.writerow([
                item["steam_app_id"],
                item["igdb_id"],
                item["title"],
                *[item["scores"][axis] for axis in AXES],
                *[item["evidence_count"][axis] for axis in AXES],
                *[item["confidence"][axis] for axis in AXES],
            ])

    lines = [
        "# 게임 취향 점수 생성 검증 보고서",
        "",
        f"- 전체 게임: {len(results)}",
        f"- 기존 규칙 연결: {connected}",
        f"- 기존 규칙 미연결: {len(unmatched)}",
        f"- 철자 오류 보정: {typo_count}",
        "- 점수 근거가 없는 Trait: null",
        "- PvP와 Online PvP: 하나의 지원 신호로 처리",
        "",
        "## Trait별 점수 생성 현황",
        "",
        "| Trait | 점수 생성 게임 | 점수 미생성 게임 | 평균 |",
        "|---|---:|---:|---:|",
    ]

    for axis in AXES:
        values = [
            item["scores"][axis]
            for item in results
            if item["scores"][axis] is not None
        ]
        average = round(sum(values) / len(values), 2) if values else "없음"
        lines.append(
            f"| {axis} | {len(values)} | {len(results) - len(values)} | {average} |"
        )

    lines.extend(["", "## 기존 규칙 미연결 항목", ""])
    if unmatched:
        for tag, axis, weight in unmatched:
            lines.append(f"- {tag} / {axis} / {weight}")
    else:
        lines.append("- 없음")

    lines.extend(["", "## 점수 분포", ""])
    for axis in AXES:
        lines.extend([f"### {axis}", ""])
        if distributions[axis]:
            for score, count in sorted(distributions[axis].items()):
                lines.append(f"- {score}: {count}개")
        else:
            lines.append("- 점수 생성 게임 없음")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("===== 점수 생성 완료 =====")
    print("전체 게임:", len(results))
    print("규칙 연결:", connected)
    print("규칙 미연결:", len(unmatched))
    print("오타 보정:", typo_count)
    print("\n생성 파일:")
    print(json_path)
    print(csv_path)
    print(report_path)
    print("\nTrait별 점수 생성 게임 수:")
    for axis in AXES:
        print(axis, evidence_totals[axis], "/", len(results))


if __name__ == "__main__":
    main()

