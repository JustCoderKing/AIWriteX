# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.research import service  # noqa: E402
from src.ai_write_x.core.research.materials import NO_MATERIALS, Materials  # noqa: E402
from src.ai_write_x.core.research.queries import (  # noqa: E402
    clean_topic,
    parse_queries,
    rule_queries,
)
from src.ai_write_x.core.research.relevance import filter_relevant, terms  # noqa: E402

TOPIC = "为什么我劝你不要过度努力"
RELEVANT = {
    "title": "研究显示：长期过度努力会导致职业倦怠",
    "abstract": "心理学研究发现，过度努力与焦虑、失眠高度相关……",
    "url": "https://a.example/1",
}
IRRELEVANT = {
    "title": "2026年最新手机排行榜",
    "abstract": "本文盘点今年销量最高的十款手机，配置与价格一览……",
    "url": "https://b.example/2",
}


def test_clean_topic_removes_colloquial():
    assert clean_topic(TOPIC) == "不要过度努力"


def test_rule_queries_keeps_original_as_fallback():
    queries = rule_queries(TOPIC)
    assert queries[0] == "不要过度努力"
    assert TOPIC in queries


def test_parse_queries():
    text = "1. 过度努力 健康 研究\n- 职业倦怠 数据\n说明：\n过度努力 健康 研究"
    assert parse_queries(text) == ["过度努力 健康 研究", "职业倦怠 数据"]


def test_terms_bigrams():
    assert terms("过度努力") == {"过度", "度努", "努力"}


def test_filter_relevant_drops_unrelated():
    kept = filter_relevant([RELEVANT, IRRELEVANT], TOPIC, ["过度努力 职业倦怠"], 0.25, 8)
    assert [item for _, item in kept] == [RELEVANT]


def test_filter_relevant_dedupes():
    kept = filter_relevant([RELEVANT, dict(RELEVANT)], TOPIC, [], 0.1, 8)
    assert len(kept) == 1


def test_materials_prompt_empty():
    assert Materials().to_prompt_block() == NO_MATERIALS


def test_materials_prompt_search_has_ignore_rule():
    block = Materials(source_type="search", items=[RELEVANT]).to_prompt_block()
    assert "必须忽略" in block
    assert RELEVANT["title"] in block


class _FakeConfig:
    def __init__(self, research):
        self.research_config = research

    @classmethod
    def factory(cls, research):
        instance = cls(research)
        return type("C", (), {"get_instance": staticmethod(lambda: instance)})


def _patch(monkeypatch, mode, results):
    monkeypatch.setattr(
        service,
        "Config",
        _FakeConfig.factory(
            {
                "mode": mode,
                "llm_query_rewrite": False,
                "llm_relevance_check": False,
                "relevance_threshold": 0.25,
                "max_materials": 8,
            }
        ),
    )
    calls = []

    def fake_search(queries):
        calls.append(queries)
        return [dict(r) for r in results]

    monkeypatch.setattr(service, "_search", fake_search)
    return calls


def test_gather_auto_keeps_only_relevant(monkeypatch):
    _patch(monkeypatch, "auto", [RELEVANT, IRRELEVANT])
    materials = service.gather_materials(TOPIC)
    assert [it["url"] for it in materials.items] == [RELEVANT["url"]]


def test_gather_auto_all_irrelevant_means_original(monkeypatch):
    _patch(monkeypatch, "auto", [IRRELEVANT])
    materials = service.gather_materials(TOPIC)
    assert materials.empty
    assert materials.to_prompt_block() == NO_MATERIALS


def test_gather_always_falls_back_to_top_results(monkeypatch):
    _patch(monkeypatch, "always", [IRRELEVANT])
    materials = service.gather_materials(TOPIC)
    assert len(materials.items) == 1


def test_gather_off_skips_search(monkeypatch):
    calls = _patch(monkeypatch, "off", [RELEVANT])
    materials = service.gather_materials(TOPIC)
    assert materials.empty
    assert calls == []
