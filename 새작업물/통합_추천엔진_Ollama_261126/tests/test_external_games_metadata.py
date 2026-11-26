from app.services.external_games import _collect_named_values, _platform_names, supports_pc_or_console


def test_external_metadata_flattens_steam_and_igdb_fields():
    detail = {
        "steam": {"genres": [{"description": "Action"}], "categories": [{"description": "Single-player"}]},
        "igdb": {"game": {
            "genres": [{"name": "Adventure"}],
            "themes": [{"name": "Fantasy"}],
            "keywords": [{"name": "Open world"}],
            "platforms": [{"name": "PC (Microsoft Windows)"}, {"name": "PlayStation 5"}],
        }},
    }
    assert _collect_named_values(detail, {"genres", "genre"}) == ["Action", "Adventure"]
    assert _collect_named_values(detail, {"categories", "themes", "keywords"}) == [
        "Single-player", "Fantasy", "Open world"
    ]
    assert _platform_names(detail["igdb"]["game"]["platforms"]) == ["PC (Microsoft Windows)", "PlayStation 5"]
    assert supports_pc_or_console(detail)


def test_mobile_only_game_is_not_supported():
    detail = {"steam": {"platforms": {"windows": False, "mac": False, "linux": False}},
              "igdb": {"game": {"platforms": [{"name": "Android"}, {"name": "iOS"}]}}}
    assert not supports_pc_or_console(detail)
