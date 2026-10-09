# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.core.crew_output_patch import (  # noqa: E402
    separate_action_and_final_answer,
)


MIXED = """Thought: 先搜索再写
Action: aiforge_search_tool
Action Input: {"topic": "测试"}
Final Answer: # 文章标题

正文已经写好了，这里是足够长的最终内容。
"""


def test_before_tool_keeps_action_only():
    text = separate_action_and_final_answer(MIXED, tool_already_used=False)
    assert "Action:" in text
    assert "Final Answer:" not in text


def test_after_tool_keeps_final_answer_only():
    text = separate_action_and_final_answer(MIXED, tool_already_used=True)
    assert "Final Answer:" in text
    assert "Action:" not in text
    assert "正文已经写好了" in text
