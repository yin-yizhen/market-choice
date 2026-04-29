import pytest

from app.services import amap


def test_search_pois_around_paginates_until_declared_count(monkeypatch):
    calls = []

    def fake_get_json(_path, params):
        calls.append(params["page"])
        page = params["page"]
        if page == 1:
            return {"status": "1", "count": "30", "pois": [{"name": f"poi-{i}"} for i in range(25)]}
        return {"status": "1", "count": "30", "pois": [{"name": f"poi-{i}"} for i in range(5)]}

    monkeypatch.setattr(amap, "_get_json", fake_get_json)

    result = amap.search_pois_around_detailed(31.2, 121.4, 3000)

    assert calls == [1, 2]
    assert result["declared_count"] == 30
    assert len(result["pois"]) == 30
    assert result["truncated"] is False


def test_search_pois_around_marks_truncated_at_page_limit(monkeypatch):
    def fake_get_json(_path, params):
        return {"status": "1", "count": "999", "pois": [{"name": f"poi-{params['page']}-{i}"} for i in range(25)]}

    monkeypatch.setattr(amap, "_get_json", fake_get_json)

    result = amap.search_pois_around_detailed(31.2, 121.4, 3000)

    assert result["pages_fetched"] == amap.MAX_PAGES
    assert len(result["pois"]) == amap.MAX_PAGES * amap.PAGE_SIZE
    assert result["truncated"] is True


def test_get_json_raises_on_amap_error(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"status":"0","info":"INVALID_USER_KEY"}'

    monkeypatch.setenv("AMAP_WEB_SERVICE_KEY", "configured")
    amap.get_settings.cache_clear()
    monkeypatch.setattr(amap.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(RuntimeError, match="INVALID_USER_KEY"):
        amap._get_json("place/around", {})
