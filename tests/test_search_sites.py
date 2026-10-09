# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.tools.search_template import (  # noqa: E402
    normalize_search_sites,
    parse_engine_html,
    parse_generic_html,
    search_enabled_sites,
)


BAIDU_HTML = """
<html><body>
<div class="result">
  <h3><a href="https://news.example.com/a">林锦岐终于懂了夫人的话</a></h3>
  <div class="c-abstract">微博热搜显示，这则故事在评论区被大量转发，讨论家庭沟通与理解。</div>
</div>
<div class="result">
  <h3><a href="https://www.baidu.com/s?wd=next">下一页</a></h3>
  <div class="c-abstract">这是翻页链接不应该被收进检索结果里面的摘要文本。</div>
</div>
</body></html>
"""

GENERIC_HTML = """
<html><body>
<ul>
  <li>
    <h3><a href="https://news.example.com/custom">自定义站点的一条新闻标题</a></h3>
    <p>这里是足够长的摘要文本，用来确认通用提取可以拿到摘要内容。</p>
  </li>
</ul>
</body></html>
"""


def test_parse_builtin_baidu_html():
    items = parse_engine_html("baidu", BAIDU_HTML, max_results=5)
    assert len(items) == 1
    assert items[0]["url"] == "https://news.example.com/a"


def test_parse_generic_html():
    items = parse_generic_html(GENERIC_HTML, max_results=3)
    assert len(items) == 1
    assert items[0]["title"] == "自定义站点的一条新闻标题"
    assert "通用提取" in items[0]["abstract"]


def test_normalize_keeps_defaults_and_valid_custom_sites():
    sites = normalize_search_sites(
        [
            {"id": "baidu", "enabled": False, "count": 2},
            {"id": "custom-1", "name": "示例", "url": "https://example.com/s?q={topic}", "count": 4},
            {"id": "bad", "name": "无效", "url": "https://example.com/s?q=fixed"},
        ]
    )
    assert [site["id"] for site in sites[:4]] == ["baidu", "sogou", "360", "bing"]
    assert sites[0]["enabled"] is False
    assert sites[0]["count"] == 2
    assert sites[0]["url"].startswith("https://www.baidu.com/")
    assert sites[-1]["id"] == "custom-1"
    assert sites[-1]["builtin"] is False
    assert all(site["id"] != "bad" for site in sites)


def test_writing_search_uses_only_enabled_sites_and_counts(monkeypatch):
    calls = []

    def fake_fetch(url_template, topic, count):
        calls.append((url_template, topic, count))
        if "baidu.com" in url_template:
            return BAIDU_HTML
        return GENERIC_HTML

    monkeypatch.setattr("src.ai_write_x.tools.search_template._fetch_search_html", fake_fetch)
    sites = normalize_search_sites(
        [
            {"id": "baidu", "enabled": True, "count": 1},
            {"id": "sogou", "enabled": False, "count": 3},
            {"id": "360", "enabled": False, "count": 3},
            {"id": "bing", "enabled": False, "count": 3},
            {
                "id": "custom-1",
                "name": "示例",
                "enabled": True,
                "count": 1,
                "url": "https://example.com/s?q={topic}",
            },
        ]
    )
    results = search_enabled_sites(sites, "测试话题")
    assert [item["source_name"] for item in results] == ["百度", "示例"]
    assert len(results) == 2
    assert all(call[2] in (1,) for call in calls)
    assert all("sogou.com" not in call[0] for call in calls)
