import asyncio

import pytest

from app.services import steam


def test_official_review_api_contract(monkeypatch):
    calls = []

    async def fake_get(url, params, timeout=15):
        calls.append((url, params, timeout))
        return {"response": {
            "query_summary": {"total_positive": 8, "total_negative": 2, "total_reviews": 10},
            "reviews": [{"review": "좋아요", "voted_up": True, "recommendationid": "1",
                         "author": {"playtime_forever": 120, "steamid": "76561198000000000"}}],
            "cursor": "next+/=",
        }}

    monkeypatch.setattr(steam, "_get_json", fake_get)
    assert asyncio.run(steam.fetch_reviews(1174180)) == [{"text": "좋아요", "voted_up": True}]
    assert asyncio.run(steam.fetch_review_summary(1174180))["total"] == 10
    page = asyncio.run(steam.fetch_review_page(1174180, sentiment="negative", language="koreana", cursor="next+/="))
    assert page["items"][0]["text"] == "좋아요"
    assert page["cursor"] == "next+/="
    payload = __import__("json").loads(calls[-1][1]["input_json"])
    assert calls[-1][0].endswith("/IUserReviewsService/GetAppReviews/v1/")
    assert payload["cursor"] == "next+/="
    assert payload["review_type"] == 2 and payload["filter"] == 1
    assert payload["languages"] == ["koreana"] and payload["purchase_type"] == 1


@pytest.mark.parametrize("response", [{}, {"response": {}}, {"response": {"reviews": "bad"}}])
def test_invalid_review_response_is_not_treated_as_empty(monkeypatch, response):
    async def fake_get(*args, **kwargs):
        return response
    monkeypatch.setattr(steam, "_get_json", fake_get)
    with pytest.raises(ValueError):
        asyncio.run(steam.fetch_reviews(1))


def test_empty_review_response_is_valid(monkeypatch):
    async def fake_get(*args, **kwargs):
        return {"response": {"query_summary": {"total_reviews": 0}, "reviews": []}}
    monkeypatch.setattr(steam, "_get_json", fake_get)
    assert asyncio.run(steam.fetch_reviews(1)) == []
    assert asyncio.run(steam.fetch_review_summary(1))["total"] == 0
