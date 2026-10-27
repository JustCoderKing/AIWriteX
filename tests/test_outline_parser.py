# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.writing.outline_parser import parse_outline  # noqa: E402

SAMPLE = """选定标题：年轻人为什么开始逃离大城市
开头钩子类型：反常识
候选标题：
- 年轻人为什么开始逃离大城市
- 北上广不再香了？
- 逃离之后，他们过得怎样
正文小标题大纲：
1. 一组反常识的数据
2. 真实原因不是房价
3. 小城生活的另一面
4. 给你的三个建议
"""


def test_parse_full():
    o = parse_outline(SAMPLE)
    assert o.selected_title == "年轻人为什么开始逃离大城市"
    assert o.hook_type == "反常识"
    assert len(o.candidate_titles) == 3
    assert len(o.sections) == 4


def test_parse_empty_fallback():
    o = parse_outline("", fallback_topic="话题A")
    assert o.selected_title == "话题A"
    assert 3 <= len(o.sections) <= 6


def test_parse_h2_sections():
    o = parse_outline("## 第一部分\n## 第二部分\n## 第三部分", fallback_topic="T")
    assert o.sections[:3] == ["第一部分", "第二部分", "第三部分"]
