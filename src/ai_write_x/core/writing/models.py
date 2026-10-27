from dataclasses import dataclass, field
from typing import List


@dataclass
class OutlineResult:
    """大纲阶段结构化结果。"""

    selected_title: str
    hook_type: str
    sections: List[str] = field(default_factory=list)
    candidate_titles: List[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        titles = self.candidate_titles or ([self.selected_title] if self.selected_title else [])
        sections = self.sections or ["背景与问题", "核心观点", "实践建议", "总结"]
        lines = [
            f"选定标题：{self.selected_title or '（待写作时拟定）'}",
            f"开头钩子类型：{self.hook_type}",
            "候选标题：",
            *[f"- {t}" for t in titles],
            "正文小标题大纲：",
            *[f"{i}. {s}" for i, s in enumerate(sections, 1)],
        ]
        return "\n".join(lines)


@dataclass
class QCReport:
    passed: bool
    reasons: List[str] = field(default_factory=list)
