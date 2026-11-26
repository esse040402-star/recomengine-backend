#!/usr/bin/env python3
"""
RecomEngine 화면_최종.html에서 React 이전에 필요한 대형 window.* 데이터와
window.ASSETS의 Base64 게임 이미지를 자동으로 분리하는 보조 스크립트입니다.

사용 예:
    python tools/extract_prototype_data.py "화면_최종.html" --frontend "./frontend"
    python tools/extract_prototype_data.py "화면_최종.html" --frontend "./frontend" --logo "웹 로고(3).png"

생성 예:
    frontend/
      public/assets/games/
      src/assets/brand/recomengine-logo.png   (logo 인자를 준 경우)
      src/data/generated/
        catalog.json
        gameDetails.json
        marketSnapshot.json
        steamReviews.json
        rankings.json
        rankingMeta.json
        profileSource.json
        prototypeAssets.generated.js
        extraction-manifest.json

주의:
- 원본 HTML은 수정하지 않습니다.
- 외부 HTTPS 이미지는 다운로드하지 않고 URL을 그대로 유지합니다.
- Base64 이미지만 실제 파일로 분리합니다.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any

WINDOW_NAMES = [
    "STEAM_REVIEWS",
    "PROFILE_SOURCE",
    "CATALOG",
    "GAME_DETAILS",
    "ASSETS",
    "MARKET_SNAPSHOT",
    "RANKINGS",
    "RANKING_META",
    "LOGO",
]

OUTPUT_NAMES = {
    "STEAM_REVIEWS": "steamReviews.json",
    "PROFILE_SOURCE": "profileSource.json",
    "CATALOG": "catalog.json",
    "GAME_DETAILS": "gameDetails.json",
    "MARKET_SNAPSHOT": "marketSnapshot.json",
    "RANKINGS": "rankings.json",
    "RANKING_META": "rankingMeta.json",
}

DATA_URL = re.compile(
    r"^data:(?P<mime>[^;,]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
    re.S,
)


def parse_window_json(source: str, name: str) -> Any:
    marker = f"window.{name}="
    pos = source.find(marker)
    if pos < 0:
        raise KeyError(f"{marker} 를 찾지 못했습니다.")

    start = pos + len(marker)
    while start < len(source) and source[start].isspace():
        start += 1

    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(source[start:])
    return value


def extension_for_mime(mime: str) -> str:
    manual = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
        "font/woff2": ".woff2",
        "font/woff": ".woff",
    }
    return manual.get(mime, mimetypes.guess_extension(mime) or ".bin")


def decode_data_url(value: str) -> tuple[str, bytes] | None:
    match = DATA_URL.match(value)
    if not match:
        return None
    mime = match.group("mime")
    raw = base64.b64decode(re.sub(r"\s+", "", match.group("data")))
    return mime, raw


def safe_name(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-")
    return cleaned or "asset"


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="화면_최종.html 경로")
    parser.add_argument(
        "--frontend",
        type=Path,
        default=Path("frontend"),
        help="React frontend 폴더 (기본: ./frontend)",
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=None,
        help="선택: 웹 로고(3).png 경로",
    )
    args = parser.parse_args()

    html_path = args.html.resolve()
    frontend = args.frontend.resolve()

    if not html_path.exists():
        raise SystemExit(f"HTML 파일이 없습니다: {html_path}")

    source = html_path.read_text(encoding="utf-8")

    generated_dir = frontend / "src" / "data" / "generated"
    game_asset_dir = frontend / "public" / "assets" / "games"
    brand_dir = frontend / "src" / "assets" / "brand"

    generated_dir.mkdir(parents=True, exist_ok=True)
    game_asset_dir.mkdir(parents=True, exist_ok=True)
    brand_dir.mkdir(parents=True, exist_ok=True)

    extracted: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for name in WINDOW_NAMES:
        try:
            extracted[name] = parse_window_json(source, name)
        except Exception as exc:
            errors[name] = str(exc)

    # JSON 데이터 분리
    for name, file_name in OUTPUT_NAMES.items():
        if name not in extracted:
            continue
        (generated_dir / file_name).write_text(
            json.dumps(extracted[name], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ASSETS 처리
    assets = extracted.get("ASSETS", {})
    generated_assets: dict[str, dict[str, str]] = {}
    asset_manifest: list[dict[str, Any]] = []

    if isinstance(assets, dict):
        for game_id, values in assets.items():
            if not isinstance(values, dict):
                continue

            game_id_safe = safe_name(str(game_id))
            generated_assets[game_id] = {}

            for kind, value in values.items():
                if not isinstance(value, str):
                    continue

                decoded = decode_data_url(value)

                if decoded:
                    mime, raw = decoded
                    ext = extension_for_mime(mime)
                    file_name = f"{game_id_safe}-{safe_name(str(kind))}{ext}"
                    target = game_asset_dir / file_name
                    target.write_bytes(raw)

                    public_path = f"/assets/games/{file_name}"
                    generated_assets[game_id][kind] = public_path
                    asset_manifest.append(
                        {
                            "gameId": game_id,
                            "kind": kind,
                            "source": "embedded-base64",
                            "mime": mime,
                            "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "output": public_path,
                        }
                    )
                elif value.startswith(("https://", "http://")):
                    generated_assets[game_id][kind] = value
                    asset_manifest.append(
                        {
                            "gameId": game_id,
                            "kind": kind,
                            "source": "external-url",
                            "output": value,
                        }
                    )
                else:
                    generated_assets[game_id][kind] = value
                    asset_manifest.append(
                        {
                            "gameId": game_id,
                            "kind": kind,
                            "source": "other",
                            "output": value,
                        }
                    )

    module_lines = [
        "// AUTO-GENERATED by extract_prototype_data.py",
        "// 원본 화면_최종.html의 window.ASSETS를 React에서 사용하기 쉽게 분리한 파일입니다.",
        "",
        "export const PROTOTYPE_ASSETS = {",
    ]

    for game_id, values in generated_assets.items():
        module_lines.append(f"  {js_string(game_id)}: {{")
        for kind, path in values.items():
            module_lines.append(
                f"    {js_string(str(kind))}: {js_string(path)},"
            )
        module_lines.append("  },")

    module_lines += [
        "};",
        "",
        "export default PROTOTYPE_ASSETS;",
        "",
    ]

    (generated_dir / "prototypeAssets.generated.js").write_text(
        "\n".join(module_lines),
        encoding="utf-8",
    )

    # 로고 복사
    logo_output = None
    if args.logo is not None:
        logo_path = args.logo.resolve()
        if not logo_path.exists():
            raise SystemExit(f"Logo 파일이 없습니다: {logo_path}")
        suffix = logo_path.suffix.lower() or ".png"
        logo_output = brand_dir / f"recomengine-logo{suffix}"
        shutil.copy2(logo_path, logo_output)

    manifest = {
        "sourceHtml": str(html_path),
        "sourceBytes": html_path.stat().st_size,
        "windowAssignmentsFound": sorted(extracted.keys()),
        "windowAssignmentErrors": errors,
        "gameAssetEntries": len(generated_assets),
        "assetItems": len(asset_manifest),
        "logoCopiedTo": str(logo_output) if logo_output else None,
        "assets": asset_manifest,
    }

    (generated_dir / "extraction-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("완료")
    print(f"- Source: {html_path}")
    print(f"- React frontend: {frontend}")
    print(f"- Game asset entries: {len(generated_assets)}")
    print(f"- Asset records: {len(asset_manifest)}")
    print(f"- Generated data: {generated_dir}")
    print(f"- Game images: {game_asset_dir}")
    if logo_output:
        print(f"- Logo: {logo_output}")
    if errors:
        print("- 일부 window 데이터 파싱 실패:")
        for key, message in errors.items():
            print(f"  {key}: {message}")


if __name__ == "__main__":
    main()
