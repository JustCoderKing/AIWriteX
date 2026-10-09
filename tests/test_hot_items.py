# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.tools import hotnews  # noqa: E402


def test_hot_items_keep_rank_heat_and_limit(monkeypatch):
    monkeypatch.setattr(
        hotnews,
        "get_zhiwei_hotnews",
        lambda platform: [
            {"name": f"话题{i}", "rank": i, "lastCount": i * 10, "url": f"https://example.com/{i}"}
            for i in range(1, 8)
        ],
    )
    monkeypatch.setattr(hotnews, "get_tophub_hotnews", lambda platform, cnt: None)
    items = hotnews.get_platform_hot_items("微博", 5)
    assert len(items) == 5
    assert items[0]["name"] == "话题1"
    assert items[0]["rank"] == 1
    assert items[0]["heat"] == "10"
    assert items[0]["url"].endswith("/1")
