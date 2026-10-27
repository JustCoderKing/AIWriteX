# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.humanize.rules import (  # noqa: E402
    flatten_lists,
    humanize_markdown,
    weaken_connectives,
)


def test_flatten_long_list():
    md = "\n".join(f"- 项{i}" for i in range(6))
    out = flatten_lists(md)
    assert "- 项" not in out
    assert "项0；项1" in out


def test_keep_short_list():
    md = "- a\n- b"
    assert flatten_lists(md) == md


def test_weaken_connectives():
    out = weaken_connectives("首先，我们看到问题。综上所述，结论如下。")
    assert "首先" not in out
    assert "综上所述" not in out


def test_humanize_keeps_headings():
    md = "# 标题\n\n## 小节\n\n首先，这是一段足够长的正文内容，用来测试人味处理是否保留结构与标题层级。"
    out = humanize_markdown(md)
    assert "# 标题" in out and "## 小节" in out
    assert "首先" not in out
