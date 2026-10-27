import hashlib
import re
import shutil
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager


def _pick(value, index: int = 0):
    if isinstance(value, list):
        if not value:
            return ""
        return value[index] if 0 <= index < len(value) else value[0]
    return value or ""


def _seed(text: str) -> str:
    return hashlib.md5((text or "img").encode("utf-8")).hexdigest()[:12]


def _font(size: int):
    for candidate in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _placeholder(path: Path, size: tuple, label: str) -> Path:
    digest = _seed(label)
    color = tuple(int(digest[i : i + 2], 16) // 2 + 60 for i in (0, 2, 4))
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    text = (label or "配图")[:20]
    font = _font(max(18, size[1] // 10))
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = len(text) * 12, 20
    draw.text(((size[0] - tw) / 2, (size[1] - th) / 2), text, fill=(255, 255, 255), font=font)
    image.save(path, "JPEG", quality=90)
    return path


def _download(url: str, path: Path, timeout: int = 10) -> bool:
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.content and len(resp.content) > 1000:
            path.write_bytes(resp.content)
            Image.open(path).verify()
            return True
    except Exception as e:
        log.print_log(f"图片下载失败 {url}: {e}", "warning")
    return False


def _ali_generate(prompt: str, path: Path) -> bool:
    try:
        from dashscope import ImageSynthesis  # type: ignore
    except Exception:
        return False
    try:
        config = Config.get_instance()
        img_cfg = config.config.get("img_api", {}).get("ali", {})
        api_key = _pick(img_cfg.get("api_key"), img_cfg.get("key_index", 0))
        model = _pick(img_cfg.get("model"), img_cfg.get("model_index", 0)) or "wanx2.0-t2i-turbo"
        if not api_key:
            return False
        rsp = ImageSynthesis.call(
            model=model, prompt=prompt, n=1, size="1024*1024", api_key=api_key
        )
        results = getattr(getattr(rsp, "output", None), "results", None) or []
        if not results:
            return False
        url = results[0].url if hasattr(results[0], "url") else results[0].get("url")
        return bool(url) and _download(url, path, timeout=30)
    except Exception as e:
        log.print_log(f"阿里生图失败，回退其他图源: {e}", "warning")
        return False


def _image_dir() -> Path:
    return PathManager.get_image_dir()


def _web_path(path: Path) -> str:
    return f"/images/{path.name}"


def obtain_image(label: str, size: tuple, *, prefix: str, prompt: Optional[str] = None) -> str:
    """
    获取一张图并保存到图片目录，返回 /images/ 路径。
    顺序：阿里生图（配置为 ali 时）→ picsum → 本地占位。
    """
    name = f"{prefix}_{_seed(label + str(size))}.jpg"
    path = _image_dir() / name
    if path.exists():
        return _web_path(path)

    config = Config.get_instance()
    img_type = ""
    try:
        img_type = config.img_api_type
    except Exception:
        pass

    if img_type == "ali" and _ali_generate(prompt or label, path):
        return _web_path(path)

    picsum = f"https://picsum.photos/seed/{_seed(label)}/{size[0]}/{size[1]}"
    if _download(picsum, path):
        return _web_path(path)

    _placeholder(path, size, label)
    return _web_path(path)


def obtain_cover(title: str) -> str:
    """生成封面并裁剪为 900x384，返回 /images/ 路径。"""
    from src.ai_write_x.utils.utils import crop_cover_image

    raw = obtain_image(title, (1200, 600), prefix="cover_raw", prompt=f"公众号封面，主题：{title}，简洁高级，无文字")
    raw_path = _image_dir() / Path(raw).name
    cropped = crop_cover_image(str(raw_path), (900, 384))
    final = _image_dir() / f"cover_{_seed(title)}.jpg"
    if cropped and Path(cropped).exists():
        shutil.move(cropped, final)
    else:
        _placeholder(final, (900, 384), title)
    return _web_path(final)


def safe_alt(text: str) -> str:
    return re.sub(r"[\[\]\(\)]", "", (text or "配图").strip())[:30] or "配图"
