# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.writing.qc import check_article, count_text_chars  # noqa: E402


GOOD_OPENING = "你有没有发现，最近身边越来越多的人开始讨论这件事，而且观点分歧越来越大，背后其实藏着一个被忽略的关键问题。"


def _article(body_len: int, opening: str = GOOD_OPENING, lists: int = 0) -> str:
    parts = ["# 标题", "", opening, ""]
    parts += [f"- 列表项{i}" for i in range(lists)]
    parts += ["", "## 小节", "", "正" * body_len]
    return "\n".join(parts)


def test_pass():
    report = check_article("好标题", _article(1200), 1000, 2000)
    assert report.passed, report.reasons


def test_too_short():
    report = check_article("好标题", _article(100), 1000, 2000)
    assert not report.passed
    assert any("字数不足" in r for r in report.reasons)


def test_short_opening():
    report = check_article("好标题", _article(1200, opening="开头。"), 1000, 2000)
    assert any("开头" in r for r in report.reasons)


def test_too_many_lists():
    content = "# 标题\n\n" + GOOD_OPENING + "\n\n" + "\n".join(f"- 项{i}" for i in range(20))
    content += "\n\n" + "正" * 1100
    report = check_article("好标题", content, 1000, 2000)
    assert any("列表过多" in r for r in report.reasons)


def test_missing_title():
    report = check_article("", _article(1200), 1000, 2000)
    assert any("标题" in r for r in report.reasons)


def test_count_chars_ignores_whitespace():
    assert count_text_chars("a b\nc") == 3
