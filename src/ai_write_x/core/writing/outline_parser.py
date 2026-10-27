import re
from typing import List

from src.ai_write_x.core.writing.hooks import DEFAULT_HOOK, HOOK_TYPES
from src.ai_write_x.core.writing.models import OutlineResult


def _extract_list_items(block: str) -> List[str]:
    items: List[str] = []
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^(?:[-*+]|\d+[\.、])\s+(.+)$", s)
        if m:
            items.append(m.group(1).strip())
    return items


def _pick_hook(text: str) -> str:
    for hook in HOOK_TYPES:
        if hook in text:
            return hook
    return DEFAULT_HOOK


def parse_outline(text: str, fallback_topic: str = "") -> OutlineResult:
    """
    从 LLM 大纲文本解析结构化结果。
    兼容简易 Markdown 标题块与列表。
    """
    raw = (text or "").strip()
    candidate_titles: List[str] = []
    sections: List[str] = []
    selected = ""
    hook = DEFAULT_HOOK

    if raw:
        # 选定标题
        m = re.search(r"选定标题[:：]\s*(.+)", raw)
        if m:
            selected = m.group(1).strip().strip("#").strip()

        # 钩子
        m = re.search(r"开头钩子(?:类型)?[:：]\s*(.+)", raw)
        if m:
            hook = _pick_hook(m.group(1))
        else:
            hook = _pick_hook(raw)

        # 候选标题块
        m = re.search(
            r"候选标题[:：]?\s*\n((?:.+\n)*?)(?=\n\s*(?:正文|小标题|大纲|开头)|$)",
            raw,
            re.IGNORECASE,
        )
        if m:
            candidate_titles = _extract_list_items(m.group(1))
        if not candidate_titles:
            # 任意 - 标题 列表前几项
            candidate_titles = _extract_list_items(raw)[:3]

        # 大纲/小标题块
        m = re.search(
            r"(?:正文小标题大纲|小标题大纲|大纲)[:：]?\s*\n((?:.+\n?)+)",
            raw,
            re.IGNORECASE,
        )
        if m:
            sections = _extract_list_items(m.group(1))
        if not sections:
            # 尝试 ## 二级标题
            sections = [
                ln.strip().lstrip("#").strip()
                for ln in raw.splitlines()
                if ln.strip().startswith("## ")
            ]

    if not selected:
        selected = candidate_titles[0] if candidate_titles else (fallback_topic or "无标题")

    if not candidate_titles:
        candidate_titles = [selected]

    if not sections:
        sections = ["背景与问题", "核心观点", "实践建议", "总结"]

    # 限制 3～6 个小标题
    if len(sections) > 6:
        sections = sections[:6]
    while len(sections) < 3:
        sections.append(f"补充要点{len(sections) + 1}")

    if hook not in HOOK_TYPES:
        hook = DEFAULT_HOOK

    return OutlineResult(
        selected_title=selected,
        hook_type=hook,
        sections=sections,
        candidate_titles=candidate_titles[:3],
    )
