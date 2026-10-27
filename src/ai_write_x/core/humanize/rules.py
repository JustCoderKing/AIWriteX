import re
from typing import List

# 常见 AI 连接词（轻度弱化）
_CONNECTIVE_PATTERNS = [
    (re.compile(r"首先[，,]?\s*"), ""),
    (re.compile(r"其次[，,]?\s*"), ""),
    (re.compile(r"再次[，,]?\s*"), ""),
    (re.compile(r"最后[，,]?\s*"), ""),
    (re.compile(r"综上所述[，,]?\s*"), "说到底，"),
    (re.compile(r"总而言之[，,]?\s*"), "总之，"),
    (re.compile(r"值得注意的是[，,]?\s*"), ""),
    (re.compile(r"不可否认的是[，,]?\s*"), ""),
    (re.compile(r"在当今(?:社会|时代)[，,]?\s*"), ""),
]


def _is_list_line(line: str) -> bool:
    s = line.strip()
    return bool(s.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+[\.、]\s+", s))


def flatten_lists(content: str, *, max_consecutive: int = 4) -> str:
    """过长连续列表转为段落。"""
    lines = content.splitlines()
    out: List[str] = []
    buf: List[str] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        if len(buf) > max_consecutive:
            items = []
            for ln in buf:
                m = re.match(r"^(?:[-*+]|\d+[\.、])\s+(.+)$", ln.strip())
                items.append(m.group(1).strip() if m else ln.strip())
            out.append("；".join(items) + "。")
            out.append("")
        else:
            out.extend(buf)
        buf = []

    for line in lines:
        if _is_list_line(line):
            buf.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def weaken_connectives(content: str) -> str:
    result = content
    for pattern, repl in _CONNECTIVE_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def vary_paragraph_lengths(content: str) -> str:
    """轻度交错：合并过碎短段。"""
    blocks = re.split(r"\n\s*\n", content)
    merged: List[str] = []
    i = 0
    while i < len(blocks):
        block = blocks[i].strip()
        if not block:
            i += 1
            continue
        if (
            i + 1 < len(blocks)
            and not block.startswith("#")
            and len(re.sub(r"\s+", "", block)) < 40
            and not blocks[i + 1].strip().startswith("#")
            and not _is_list_line(block)
        ):
            nxt = blocks[i + 1].strip()
            if nxt and not _is_list_line(nxt):
                merged.append(f"{block}{nxt}")
                i += 2
                continue
        merged.append(block)
        i += 1
    return "\n\n".join(merged)


def inject_subjective_touch(content: str, *, intensity: str = "low") -> str:
    """极轻度主观表达：仅在 intensity=medium 时往首段后插一句。"""
    if intensity != "medium":
        return content
    blocks = re.split(r"\n\s*\n", content.strip(), maxsplit=2)
    if len(blocks) < 2:
        return content
    # 跳过标题块
    idx = 0
    if blocks[0].lstrip().startswith("#"):
        idx = 1
    if idx >= len(blocks):
        return content
    touch = "说真的，这件事比表面上看到的更值得琢磨。"
    if touch in content:
        return content
    blocks.insert(idx + 1, touch)
    return "\n\n".join(blocks)


def humanize_markdown(content: str, *, intensity: str = "low") -> str:
    if not content:
        return content
    text = flatten_lists(content)
    text = weaken_connectives(text)
    text = vary_paragraph_lengths(text)
    text = inject_subjective_touch(text, intensity=intensity)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
