# -*- coding: utf-8 -*-
"""把文章里打不开的图片换成应用内可预览的本地图片。"""

import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from src.ai_write_x.utils.path_manager import PathManager

IMG_SRC_RE = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*[\"'])([^\"']+)([\"'])",
    re.IGNORECASE,
)
BROKEN_HOSTS = ("picsum.photos", "via.placeholder.com", "placeholder.com", "placehold.co")


def article_image_dir() -> Path:
    directory = PathManager.get_article_dir() / "_images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def is_local_media_src(src: str) -> bool:
    return src.startswith("/api/articles/media?")


def needs_replacement(src: str) -> bool:
    value = (src or "").strip()
    if not value or is_local_media_src(value):
        return False
    if value.startswith("data:"):
        return False
    lowered = value.lower()
    if any(host in lowered for host in BROKEN_HOSTS):
        return True
    if lowered.startswith(("http://", "https://")):
        return True
    return True


def optimize_article_images(html: str, article_key: str) -> tuple[str, int]:
    """替换不可看的图片地址，返回新 HTML 和替换数量。"""
    if not html or "<img" not in html.lower():
        return html, 0

    replaced = 0

    def swap(match: re.Match) -> str:
        nonlocal replaced
        src = match.group(2)
        if not needs_replacement(src):
            return match.group(0)
        alt = _alt_near(html, match.start())
        name = _write_placeholder(article_key, replaced + 1, alt or "配图")
        replaced += 1
        return f"{match.group(1)}/api/articles/media?name={name}{match.group(3)}"

    return IMG_SRC_RE.sub(swap, html), replaced


def resolve_media_file(name: str) -> Path:
    filename = Path(name or "").name
    if not filename or filename != name:
        raise ValueError("无效图片")
    path = (article_image_dir() / filename).resolve()
    root = article_image_dir().resolve()
    if root not in path.parents and path != root:
        raise ValueError("无效图片")
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path


def _alt_near(html: str, index: int) -> str:
    snippet = html[index : index + 240]
    match = re.search(r'alt\s*=\s*["\']([^"\']*)', snippet, re.IGNORECASE)
    return (match.group(1) if match else "").strip()[:24]


def _write_placeholder(article_key: str, index: int, label: str) -> str:
    digest = hashlib.md5(f"{article_key}:{index}:{label}".encode("utf-8")).hexdigest()[:10]
    filename = f"{_safe_key(article_key)}_{index}_{digest}.png"
    path = article_image_dir() / filename
    if path.exists():
        return filename

    image = Image.new("RGB", (800, 450), _color_for(digest))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 800, 12), fill=(255, 255, 255))
    text = label or "配图"
    font = ImageFont.load_default()
    for candidate in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if Path(candidate).exists():
            font = ImageFont.truetype(candidate, 36)
            break
    draw.text((36, 190), text, fill=(255, 255, 255), font=font)
    image.save(path, format="PNG")
    return filename


def _safe_key(article_key: str) -> str:
    stem = Path(article_key).stem
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", stem).strip("_")
    return (cleaned or "article")[:40]


def _color_for(digest: str) -> tuple[int, int, int]:
    seed = int(digest[:6], 16)
    return (40 + seed % 80, 70 + (seed // 8) % 90, 110 + (seed // 16) % 80)


def extract_article_text(html: str) -> tuple[str, str]:
    """从现有文章取出标题和纯文本，供换模板时重新填充。"""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    heading = soup.find(["h1", "h2"])
    title = heading.get_text(" ", strip=True) if heading else ""
    text = soup.get_text("\n", strip=True)
    return title, text
