# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.base_framework import ContentResult  # noqa: E402
from src.ai_write_x.core.research.materials import Materials  # noqa: E402
from src.ai_write_x.core.writing import pipeline as pipeline_mod  # noqa: E402
from src.ai_write_x.core.writing.models import OutlineResult  # noqa: E402

BRACED = {"title": "代码示例 {a: 1}", "abstract": "JSON 形如 {\"k\": \"v\"} 的内容", "url": "u"}


class _Cfg:
    min_article_len = 1000
    max_article_len = 2000


class _Engine:
    """模拟 CrewAI：用 str.format 填充描述，与 crewai.Task 行为一致。"""

    rendered = []

    def __init__(self, workflow):
        self.workflow = workflow

    def execute_workflow(self, inputs):
        for task in self.workflow.tasks:
            _Engine.rendered.append(task.description.format(**inputs))
        return ContentResult(title="T", content="选定标题：T", summary="", content_format="markdown")


def test_prompts_format_with_braced_materials(monkeypatch):
    monkeypatch.setattr(pipeline_mod, "ContentGenerationEngine", _Engine)
    monkeypatch.setattr(
        pipeline_mod.Config, "get_instance", staticmethod(lambda: _Cfg())
    )
    _Engine.rendered = []
    materials = Materials(source_type="search", items=[BRACED])
    outline = OutlineResult(selected_title="标题{x}", hook_type="反常识", sections=["a {b}", "c", "d"])
    p = pipeline_mod.WritingPipeline()

    p._generate_outline("题目", materials, True)
    p._generate_article("题目", materials, outline, platform="")
    p._rewrite_article("题目", ContentResult("T", "正文 {y}", "", "markdown"), ["字数不足"], outline)

    assert len(_Engine.rendered) == 3
    assert "{a: 1}" in _Engine.rendered[0]
    assert "标题{x}" in _Engine.rendered[1]
    assert "正文 {y}" in _Engine.rendered[2]
