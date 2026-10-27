import re
from typing import List, Tuple


def find_inline_slots(markdown: str, min_count: int, max_count: int) -> List[int]:
    """
    返回适合插入图片的字符偏移（在空行后、标题/段前）。
    规则：文首不插；相邻至少隔一段；数量落在 [min, max]。
    """
    if not markdown or max_count <= 0:
        return []

    lines = markdown.splitlines(keepends=True)
    # 累计偏移与段落边界（空行之后的下一非空行起点）
    candidates: List[int] = []
    offset = 0
    seen_body = False
    prev_blank = True
    paragraph_index = 0

    for line in lines:
        stripped = line.strip()
        is_blank = not stripped
        if not is_blank:
            if prev_blank and seen_body:
                # 段起始
                if stripped.startswith("## ") or (
                    not stripped.startswith("#") and paragraph_index > 0
                ):
                    candidates.append(offset)
                paragraph_index += 1
            seen_body = True
        prev_blank = is_blank
        offset += len(line)

    if not candidates:
        return []

    # 稀疏采样，保证间隔
    selected: List[int] = []
    last_para = -999
    para_map = {c: i for i, c in enumerate(candidates)}
    for c in candidates:
        pi = para_map[c]
        if selected and pi - last_para < 2:
            continue
        selected.append(c)
        last_para = pi
        if len(selected) >= max_count:
            break

    if len(selected) < min_count and len(candidates) >= min_count:
        # 回退：均匀取
        step = max(1, len(candidates) // min_count)
        selected = candidates[::step][:max_count]

    return selected[:max_count]


def insert_images_at_offsets(
    markdown: str, slots: List[int], image_markdowns: List[str]
) -> str:
    """从后往前插入，避免偏移错乱。"""
    pairs: List[Tuple[int, str]] = list(zip(slots, image_markdowns))
    pairs.sort(key=lambda x: x[0], reverse=True)
    result = markdown
    for offset, md in pairs:
        insert = md if md.endswith("\n") else md + "\n"
        if offset > 0 and result[offset - 1] != "\n":
            insert = "\n\n" + insert
        if offset < len(result) and not insert.endswith("\n\n"):
            insert = insert + "\n"
        result = result[:offset] + insert + result[offset:]
    return result
