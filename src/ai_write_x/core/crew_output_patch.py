# -*- coding: utf-8 -*-
"""兼容同时输出工具调用和最终答案的模型回复。"""

import re

_INSTALLED = False
_ACTION_RE = re.compile(
    r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)",
    re.DOTALL,
)


def separate_action_and_final_answer(text: str, tool_already_used: bool) -> str:
    """同一次回复里不能既调用工具又给最终答案。按是否已经用过工具保留其中一种。"""
    if not text or "Final Answer:" not in text or not _ACTION_RE.search(text):
        return text

    if tool_already_used:
        head, tail = text.split("Final Answer:", 1)
        head = re.sub(r"\n*Action\s*\d*\s*:.*", "\n", head, count=1, flags=re.DOTALL)
        tail = re.sub(r"\n+Action\s*\d*\s*:.*", "", tail, count=1, flags=re.DOTALL)
        return f"{head.rstrip()}\nFinal Answer:{tail}"

    return re.split(r"\n*Final Answer:", text, maxsplit=1)[0].strip()


def install_crew_output_patch() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from crewai.agents.parser import CrewAgentParser

    original_parse = CrewAgentParser.parse

    def parse(self, text: str):
        tool_results = getattr(self.agent, "tools_results", None) or []
        text = separate_action_and_final_answer(text, bool(tool_results))
        return original_parse(self, text)

    CrewAgentParser.parse = parse
    _INSTALLED = True
