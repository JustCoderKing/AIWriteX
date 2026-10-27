import json
import re
from pathlib import Path
from typing import List

from src.ai_write_x.core.base_framework import ContentResult
from src.ai_write_x.core.imaging.placement import find_inline_slots, insert_images_at_offsets
from src.ai_write_x.utils import log

_PICSUM_SRC = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*[\"'])(https?://[^\"']*(?:picsum\.photos|placeholder)[^\"']*)([\"'])",
    re.IGNORECASE,
)


def _heading_before(markdown: str, offset: int, fallback: str) -> str:
    head = markdown[:offset]
    matches = re.findall(r"^#{2,3}\s+(.+)$", head, re.MULTILINE)
    return matches[-1].strip() if matches else fallback


def apply_imaging(content: ContentResult, *, title: str, config: dict) -> ContentResult:
    """对 Markdown 成稿插入文内图，并生成封面（写入 metadata）。"""
    from src.ai_write_x.core.imaging.sources import obtain_cover, obtain_image, safe_alt

    cover_enabled = bool(config.get("cover_enabled", True))
    inline_enabled = bool(config.get("inline_enabled", True))
    inline_min = int(config.get("inline_min", 2) or 0)
    inline_max = int(config.get("inline_max", 4) or 0)

    metadata = dict(content.metadata or {})
    body = content.content or ""
    article_title = content.title or title

    if cover_enabled:
        try:
            metadata["cover"] = obtain_cover(article_title)
            log.print_log(f"封面已生成: {metadata['cover']}")
        except Exception as e:
            log.print_log(f"封面生成失败，跳过: {e}", "warning")

    inline_urls: List[str] = []
    if inline_enabled and inline_max > 0 and "![" not in body:
        try:
            slots = find_inline_slots(body, inline_min, inline_max)
            images_md = []
            for i, slot in enumerate(slots, 1):
                alt = safe_alt(_heading_before(body, slot, article_title))
                url = obtain_image(f"{article_title}-{alt}-{i}", (800, 450), prefix="inline", prompt=f"{alt}，配图，写实风格，无文字")
                inline_urls.append(url)
                images_md.append(f"![{alt}]({url})\n")
            if slots:
                body = insert_images_at_offsets(body, slots, images_md)
                log.print_log(f"已插入文内图 {len(slots)} 张")
        except Exception as e:
            log.print_log(f"文内配图失败，跳过: {e}", "warning")

    metadata["inline_images"] = inline_urls
    return ContentResult(
        title=content.title,
        content=body,
        summary=content.summary,
        content_format=content.content_format,
        metadata=metadata,
        created_at=content.created_at,
        content_type=content.content_type,
    )


def replace_placeholder_images(html: str, urls: List[str]) -> str:
    """模板/设计 HTML 中的 picsum 占位按顺序替换为本次生成图。"""
    if not html or not urls:
        return html
    queue = list(urls)

    def swap(m: re.Match) -> str:
        if not queue:
            return m.group(0)
        return f"{m.group(1)}{queue.pop(0)}{m.group(3)}"

    return _PICSUM_SRC.sub(swap, html)


def write_cover_design(article_path: str, cover: str) -> None:
    """把封面写入 .design.json（保留已有字段）。"""
    if not article_path or not cover:
        return
    design_path = Path(article_path).with_suffix(".design.json")
    data = {"html": "", "css": "", "cover": cover}
    if design_path.exists():
        try:
            data.update(json.loads(design_path.read_text(encoding="utf-8")))
            data["cover"] = cover
        except Exception:
            pass
    design_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
