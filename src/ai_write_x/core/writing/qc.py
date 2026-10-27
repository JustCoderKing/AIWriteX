import re
from typing import List

from src.ai_write_x.core.writing.models import QCReport


def count_text_chars(content: str) -> int:
    """统计纯文本字数（去空白）。"""
    if not content:
        return 0
    # 去掉 markdown 标记的粗略处理
    text = re.sub(r"[#>*_`\-\[\]\(\)!]", "", content)
    text = re.sub(r"\s+", "", text)
    return len(text)


def _first_paragraph(content: str) -> str:
    if not content:
        return ""
    # 跳过标题行
    lines = content.strip().splitlines()
    body_lines: List[str] = []
    started = False
    for line in lines:
        if not started:
            if line.strip().startswith("#"):
                continue
            if not line.strip():
                continue
            started = True
        if started and not line.strip():
            break
        if started:
            body_lines.append(line.strip())
    return "".join(body_lines)


def _list_line_ratio(content: str) -> float:
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    list_lines = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+[\.、]\s+", s):
            list_lines += 1
    return list_lines / len(lines)


def check_article(
    title: str,
    content: str,
    min_len: int,
    max_len: int,
    *,
    min_opening_chars: int = 40,
    max_list_ratio: float = 0.45,
) -> QCReport:
    """规则质检：字数、标题、开头、列表密度。"""
    reasons: List[str] = []

    if not (title or "").strip() or title.strip().lower() in {"untitled", "无标题"}:
        reasons.append("缺少有效标题")

    char_count = count_text_chars(content)
    if char_count < min_len:
        reasons.append(f"字数不足：{char_count} < {min_len}")
    elif char_count > int(max_len * 1.25):
        # 允许少量超出，超过 25% 才判失败
        reasons.append(f"字数过多：{char_count} > {max_len}")

    opening = _first_paragraph(content)
    if len(re.sub(r"\s+", "", opening)) < min_opening_chars:
        reasons.append("开头过短或空泛")

    ratio = _list_line_ratio(content)
    if ratio > max_list_ratio:
        reasons.append(f"列表过多：占比 {ratio:.0%} > {max_list_ratio:.0%}")

    return QCReport(passed=len(reasons) == 0, reasons=reasons)
